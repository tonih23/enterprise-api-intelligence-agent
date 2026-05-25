"""Unit tests for the OpenSearch chunk storage contract."""

from typing import Any

from app.rag.chunking import DocumentChunk
from app.rag.opensearch_client import OpenSearchChunkIndex


class FakeIndices:
    """Small indices stub used to inspect mapping creation."""

    def __init__(self) -> None:
        self.created_body: dict[str, Any] | None = None

    def exists(self, *, index: str) -> bool:
        return False

    def create(self, *, index: str, body: dict[str, Any]) -> None:
        self.created_body = body


class FakeClient:
    """OpenSearch-like client holding fake index operations."""

    def __init__(self) -> None:
        self.indices = FakeIndices()


def test_ensure_index_configures_knn_embedding_mapping() -> None:
    client = FakeClient()
    index = OpenSearchChunkIndex(client, "test_chunks")  # type: ignore[arg-type]

    index.ensure_index(384)

    assert client.indices.created_body is not None
    properties = client.indices.created_body["mappings"]["properties"]
    assert properties["text"]["type"] == "text"
    assert properties["source_path"]["type"] == "keyword"
    assert properties["embedding"]["type"] == "knn_vector"
    assert properties["embedding"]["dimension"] == 384


def test_index_chunks_writes_text_metadata_embedding_and_source_path(
    monkeypatch: Any,
) -> None:
    captured_actions: list[dict[str, Any]] = []

    def fake_bulk(
        client: FakeClient, actions: list[dict[str, Any]], *, refresh: bool
    ) -> tuple[int, list[object]]:
        captured_actions.extend(actions)
        assert refresh is True
        return len(actions), []

    monkeypatch.setattr("app.rag.opensearch_client.helpers.bulk", fake_bulk)
    client = FakeClient()
    index = OpenSearchChunkIndex(client, "test_chunks")  # type: ignore[arg-type]
    chunk = DocumentChunk(
        chunk_id="stable-id",
        text="Synthetic API guidance.",
        metadata={"api_name": "hcp_search_api", "synthetic": True},
        source_path="data/docs/catalogue.md",
        chunk_index=0,
    )

    indexed = index.index_chunks([chunk], [[0.1, 0.2]])

    source = captured_actions[0]["_source"]
    assert indexed == 1
    assert source["text"] == chunk.text
    assert source["metadata"] == chunk.metadata
    assert source["embedding"] == [0.1, 0.2]
    assert source["source_path"] == chunk.source_path
