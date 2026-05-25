"""End-to-end ingestion of synthetic source artifacts into OpenSearch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.rag.chunking import chunk_documents, load_documents
from app.rag.embeddings import create_embedder
from app.rag.opensearch_client import OpenSearchChunkIndex, create_opensearch_client

DEFAULT_DATA_ROOT = Path(__file__).parents[2] / "data"


@dataclass(frozen=True)
class IngestionResult:
    """Counts and destination for a completed corpus indexing run."""

    document_count: int
    chunk_count: int
    indexed_count: int
    index_name: str


def ingest_corpus(
    settings: Settings,
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> IngestionResult:
    """Load, embed, and index every supported synthetic corpus file."""

    documents = load_documents(data_root)
    chunks = chunk_documents(
        documents,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    client = create_opensearch_client(
        settings.opensearch_url,
        username=settings.opensearch_username,
        password=settings.opensearch_password,
        verify_certs=settings.opensearch_verify_certs,
    )
    if not client.ping():
        raise ConnectionError(
            f"OpenSearch is unavailable at {settings.opensearch_url!r}"
        )

    embedder = create_embedder(
        settings.embedding_backend,
        model_name=settings.embedding_model_name,
        batch_size=settings.embedding_batch_size,
    )
    index = OpenSearchChunkIndex(client, settings.opensearch_index_name)
    index.ensure_index(embedder.dimension)
    embeddings = embedder.embed_texts([chunk.text for chunk in chunks])
    indexed_count = index.index_chunks(chunks, embeddings)

    return IngestionResult(
        document_count=len(documents),
        chunk_count=len(chunks),
        indexed_count=indexed_count,
        index_name=settings.opensearch_index_name,
    )
