"""OpenSearch client construction and index writes for RAG chunks."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse

from opensearchpy import OpenSearch, helpers
from pydantic import SecretStr

from app.rag.chunking import DocumentChunk


def create_opensearch_client(
    url: str,
    *,
    username: str | None = None,
    password: SecretStr | None = None,
    verify_certs: bool = False,
) -> OpenSearch:
    """Create an OpenSearch client for either local HTTP or secured HTTPS."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Invalid OpenSearch URL: {url}")
    client_options: dict[str, object] = {
        "hosts": [
            {
                "host": parsed.hostname,
                "port": parsed.port or (443 if parsed.scheme == "https" else 9200),
            }
        ],
        "use_ssl": parsed.scheme == "https",
        "verify_certs": verify_certs,
    }
    if username and password:
        client_options["http_auth"] = (username, password.get_secret_value())
    return OpenSearch(**client_options)


class OpenSearchChunkIndex:
    """Manage the vector index and bulk-write enriched document chunks."""

    def __init__(self, client: OpenSearch, index_name: str) -> None:
        self.client = client
        self.index_name = index_name

    def ensure_index(self, embedding_dimension: int) -> None:
        """Create a k-NN index once and reject incompatible dimensions."""

        if self.client.indices.exists(index=self.index_name):
            mapping = self.client.indices.get_mapping(index=self.index_name)
            try:
                existing_dimension = mapping[self.index_name]["mappings"]["properties"][
                    "embedding"
                ]["dimension"]
            except KeyError as error:
                raise ValueError(
                    f"Index {self.index_name!r} has no compatible embedding mapping"
                ) from error
            if existing_dimension != embedding_dimension:
                raise ValueError(
                    f"Index {self.index_name!r} expects vectors of dimension "
                    f"{existing_dimension}, not {embedding_dimension}"
                )
            return

        self.client.indices.create(
            index=self.index_name,
            body={
                "settings": {"index": {"knn": True}},
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "text": {"type": "text"},
                        "source_path": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "metadata": {
                            "properties": {
                                "api_name": {"type": "keyword"},
                                "data_classification": {"type": "keyword"},
                                "domain": {"type": "keyword"},
                                "owner": {"type": "keyword"},
                                "source_type": {"type": "keyword"},
                                "synthetic": {"type": "boolean"},
                                "system": {"type": "keyword"},
                                "version": {"type": "keyword"},
                            }
                        },
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": embedding_dimension,
                            "method": {
                                "name": "hnsw",
                                "engine": "lucene",
                                "space_type": "cosinesimil",
                            },
                        },
                    }
                },
            },
        )

    def index_chunks(
        self, chunks: Sequence[DocumentChunk], embeddings: Sequence[list[float]]
    ) -> int:
        """Bulk-index chunks and vectors, replacing stable chunk identifiers."""

        if len(chunks) != len(embeddings):
            raise ValueError("Every chunk must have one embedding vector")
        actions = [
            {
                "_op_type": "index",
                "_index": self.index_name,
                "_id": chunk.chunk_id,
                "_source": {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                    "embedding": embedding,
                    "source_path": chunk.source_path,
                    "chunk_index": chunk.chunk_index,
                },
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        if not actions:
            return 0
        indexed, _ = helpers.bulk(self.client, actions, refresh=True)
        return indexed
