"""Tests for keyword, vector, hybrid, and HTTP retrieval behavior."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.rag.retriever import RagRetriever, get_retriever
from app.rag.schemas import RetrievedChunk, SearchFilters, SearchRequest


def make_hit(chunk_id: str, score: float) -> dict[str, Any]:
    """Build a minimal OpenSearch hit returned to the retriever."""

    return {
        "_id": chunk_id,
        "_score": score,
        "_source": {
            "chunk_id": chunk_id,
            "text": f"Text for {chunk_id}",
            "source_path": f"data/docs/{chunk_id}.md",
            "metadata": {"api_name": "clinical_trials_api"},
        },
    }


def search_response(*hits: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal OpenSearch search result."""

    return {"hits": {"hits": list(hits)}}


class FakeOpenSearch:
    """Record search DSL and return queued results."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def search(self, *, index: str, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"index": index, "body": body})
        return self.responses.pop(0)


class FakeEmbedder:
    """Return a predictable query vector without any model dependency."""

    dimension = 3

    def __init__(self) -> None:
        self.texts: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.texts.append(texts)
        return [[0.2, 0.4, 0.6]]


def test_keyword_search_builds_bm25_query_with_all_metadata_filters() -> None:
    client = FakeOpenSearch([search_response(make_hit("keyword-hit", 4.2))])
    retriever = RagRetriever(client, "chunks")  # type: ignore[arg-type]
    filters = SearchFilters(
        domain="research_operations",
        system="atlas_trial_registry_sandbox",
        api_name="clinical_trials_api",
        data_classification="synthetic_internal",
    )

    results = retriever.search(
        SearchRequest(query="trial sites", top_k=3, mode="keyword", filters=filters)
    )

    body = client.calls[0]["body"]
    assert body["query"]["bool"]["must"] == [
        {"match": {"text": {"query": "trial sites"}}}
    ]
    assert body["query"]["bool"]["filter"] == [
        {"term": {"metadata.domain": "research_operations"}},
        {"term": {"metadata.system": "atlas_trial_registry_sandbox"}},
        {"term": {"metadata.api_name": "clinical_trials_api"}},
        {"term": {"metadata.data_classification": "synthetic_internal"}},
    ]
    assert results[0].retrieval_mode == "keyword"
    assert results[0].score == 4.2


def test_vector_search_embeds_query_and_builds_filtered_knn_query() -> None:
    client = FakeOpenSearch([search_response(make_hit("vector-hit", 0.9))])
    embedder = FakeEmbedder()
    retriever = RagRetriever(client, "chunks", embedder)  # type: ignore[arg-type]

    results = retriever.search(
        SearchRequest(
            query="which study is currently enrolling",
            top_k=2,
            mode="vector",
            filters=SearchFilters(api_name="clinical_trials_api"),
        )
    )

    knn_options = client.calls[0]["body"]["query"]["knn"]["embedding"]
    assert embedder.texts == [["which study is currently enrolling"]]
    assert knn_options == {
        "vector": [0.2, 0.4, 0.6],
        "k": 2,
        "filter": {
            "bool": {"filter": [{"term": {"metadata.api_name": "clinical_trials_api"}}]}
        },
    }
    assert results[0].retrieval_mode == "vector"


def test_hybrid_search_uses_rrf_to_promote_result_in_both_rankings() -> None:
    client = FakeOpenSearch(
        [
            search_response(make_hit("keyword-only", 20.0), make_hit("shared", 8.0)),
            search_response(make_hit("shared", 0.99), make_hit("vector-only", 0.95)),
        ]
    )
    retriever = RagRetriever(client, "chunks", FakeEmbedder())  # type: ignore[arg-type]

    results = retriever.search(
        SearchRequest(query="find recruiting cardiology trial", top_k=2, mode="hybrid")
    )

    assert [result.chunk_id for result in results] == ["shared", "keyword-only"]
    assert all(result.retrieval_mode == "hybrid" for result in results)
    assert client.calls[0]["body"]["size"] == 10
    assert client.calls[1]["body"]["size"] == 10


def test_rag_search_endpoint_returns_typed_retrieval_results() -> None:
    app = create_app(Settings(environment="test", embedding_backend="local_hashing"))

    class StubRetriever:
        def search(self, request: SearchRequest) -> list[RetrievedChunk]:
            assert request.mode == "hybrid"
            return [
                RetrievedChunk(
                    chunk_id="chunk-1",
                    text="A synthetic trial requires approval.",
                    score=0.03,
                    source_path="data/docs/api_governance_runbook.md",
                    metadata={"api_name": "governance_controls"},
                    retrieval_mode="hybrid",
                )
            ]

    app.dependency_overrides[get_retriever] = StubRetriever
    with TestClient(app) as client:
        response = client.post(
            "/rag/search",
            json={
                "query": "Which operation needs approval?",
                "top_k": 3,
                "mode": "hybrid",
                "filters": {"data_classification": "synthetic_internal"},
            },
        )

    assert response.status_code == 200
    assert response.json()["mode"] == "hybrid"
    assert response.json()["results"][0]["chunk_id"] == "chunk-1"
    assert response.json()["results"][0]["retrieval_mode"] == "hybrid"


def test_rag_search_endpoint_reports_embedding_backend_failure() -> None:
    app = create_app(Settings(environment="test", embedding_backend="local_hashing"))

    class UnavailableRetriever:
        def search(self, request: SearchRequest) -> list[RetrievedChunk]:
            raise OSError("embedding backend unavailable")

    app.dependency_overrides[get_retriever] = UnavailableRetriever
    with TestClient(app) as client:
        response = client.post(
            "/rag/search",
            json={"query": "Which operation needs approval?", "mode": "hybrid"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Retrieval service is unavailable."


def test_rag_search_reports_missing_local_embedding_model_without_loading(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            embedding_backend="sentence_transformers",
            embedding_model_name=str(tmp_path / "missing-model"),
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/rag/search",
            json={"query": "exact endpoint", "mode": "keyword"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Retrieval service is unavailable."
