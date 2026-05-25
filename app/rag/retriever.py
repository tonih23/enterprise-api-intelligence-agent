"""BM25, vector, and hybrid retrieval over indexed synthetic documents."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from opensearchpy import OpenSearch
from opensearchpy.exceptions import OpenSearchException

from app.config import EmbeddingBackend, Settings, get_settings
from app.rag.embeddings import Embedder, create_embedder
from app.rag.opensearch_client import create_opensearch_client
from app.rag.schemas import (
    RetrievalMode,
    RetrievedChunk,
    SearchFilters,
    SearchRequest,
    SearchResponse,
)

RRF_RANK_CONSTANT = 60
RETRIEVAL_UNAVAILABLE_DETAIL = "Retrieval service is unavailable."
router = APIRouter(prefix="/rag", tags=["rag"])


def _metadata_filter_clauses(filters: SearchFilters | None) -> list[dict[str, Any]]:
    if filters is None:
        return []
    return [
        {"term": {f"metadata.{field}": value}}
        for field, value in filters.model_dump(exclude_none=True).items()
    ]


def _hits_to_chunks(
    hits: Sequence[dict[str, Any]], retrieval_mode: RetrievalMode
) -> list[RetrievedChunk]:
    results = []
    for hit in hits:
        source = hit["_source"]
        results.append(
            RetrievedChunk(
                chunk_id=source.get("chunk_id", hit["_id"]),
                text=source["text"],
                score=float(hit.get("_score") or 0.0),
                source_path=source["source_path"],
                metadata=source.get("metadata", {}),
                retrieval_mode=retrieval_mode,
            )
        )
    return results


class RagRetriever:
    """Retrieve chunks with lexical, vector, or rank-fused strategies."""

    def __init__(
        self,
        client: OpenSearch,
        index_name: str,
        embedder: Embedder | None = None,
    ) -> None:
        self.client = client
        self.index_name = index_name
        self.embedder = embedder

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        """Execute the retrieval mode requested by the caller."""

        if request.mode == "keyword":
            return self.keyword_search(request.query, request.top_k, request.filters)
        if request.mode == "vector":
            return self.vector_search(request.query, request.top_k, request.filters)
        return self.hybrid_search(request.query, request.top_k, request.filters)

    def keyword_search(
        self, query: str, top_k: int, filters: SearchFilters | None = None
    ) -> list[RetrievedChunk]:
        """Search indexed text using OpenSearch's default BM25 similarity."""

        match_query: dict[str, Any] = {"match": {"text": {"query": query}}}
        filter_clauses = _metadata_filter_clauses(filters)
        search_query: dict[str, Any] = match_query
        if filter_clauses:
            search_query = {"bool": {"must": [match_query], "filter": filter_clauses}}
        response = self.client.search(
            index=self.index_name,
            body={
                "size": top_k,
                "_source": ["chunk_id", "text", "source_path", "metadata"],
                "query": search_query,
            },
        )
        return _hits_to_chunks(response["hits"]["hits"], "keyword")

    def vector_search(
        self, query: str, top_k: int, filters: SearchFilters | None = None
    ) -> list[RetrievedChunk]:
        """Embed a query and execute k-nearest-neighbor vector retrieval."""

        if self.embedder is None:
            raise ValueError("Vector retrieval requires a configured embedder")
        query_vector = self.embedder.embed_texts([query])[0]
        knn_options: dict[str, Any] = {"vector": query_vector, "k": top_k}
        filter_clauses = _metadata_filter_clauses(filters)
        if filter_clauses:
            knn_options["filter"] = {"bool": {"filter": filter_clauses}}
        response = self.client.search(
            index=self.index_name,
            body={
                "size": top_k,
                "_source": ["chunk_id", "text", "source_path", "metadata"],
                "query": {"knn": {"embedding": knn_options}},
            },
        )
        return _hits_to_chunks(response["hits"]["hits"], "vector")

    def hybrid_search(
        self, query: str, top_k: int, filters: SearchFilters | None = None
    ) -> list[RetrievedChunk]:
        """Fuse BM25 and vector rankings with reciprocal rank fusion."""

        candidate_count = max(top_k * 2, 10)
        ranked_results = (
            self.keyword_search(query, candidate_count, filters),
            self.vector_search(query, candidate_count, filters),
        )
        chunks_by_id: dict[str, RetrievedChunk] = {}
        fused_scores: dict[str, float] = {}
        for candidates in ranked_results:
            for rank, chunk in enumerate(candidates, start=1):
                chunks_by_id.setdefault(chunk.chunk_id, chunk)
                fused_scores[chunk.chunk_id] = fused_scores.get(chunk.chunk_id, 0.0) + (
                    1.0 / (RRF_RANK_CONSTANT + rank)
                )

        ranked_ids = sorted(
            fused_scores,
            key=lambda chunk_id: (-fused_scores[chunk_id], chunk_id),
        )[:top_k]
        return [
            chunks_by_id[chunk_id].model_copy(
                update={
                    "score": fused_scores[chunk_id],
                    "retrieval_mode": "hybrid",
                }
            )
            for chunk_id in ranked_ids
        ]


@lru_cache(maxsize=8)
def _cached_embedder(
    backend: EmbeddingBackend, model_name: str, batch_size: int
) -> Embedder:
    """Retain loaded semantic models between vector-search requests."""

    return create_embedder(backend, model_name=model_name, batch_size=batch_size)


def get_retriever(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RagRetriever:
    """Build the configured search service for an API request."""

    client = create_opensearch_client(
        settings.opensearch_url,
        username=settings.opensearch_username,
        password=settings.opensearch_password,
        verify_certs=settings.opensearch_verify_certs,
    )
    try:
        embedder = _cached_embedder(
            settings.embedding_backend,
            settings.embedding_model_name,
            settings.embedding_batch_size,
        )
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=RETRIEVAL_UNAVAILABLE_DETAIL,
        ) from error
    return RagRetriever(client, settings.opensearch_index_name, embedder)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Retrieve documentation chunks",
)
def search_documents(
    request: SearchRequest,
    retriever: Annotated[RagRetriever, Depends(get_retriever)],
) -> SearchResponse:
    """Return ranked synthetic documentation evidence for a query."""

    try:
        results = retriever.search(request)
    except (OpenSearchException, OSError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=RETRIEVAL_UNAVAILABLE_DETAIL,
        ) from error
    return SearchResponse(query=request.query, mode=request.mode, results=results)
