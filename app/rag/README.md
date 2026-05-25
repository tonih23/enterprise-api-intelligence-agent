# RAG Ingestion Module

The `app.rag` package prepares the fictional API corpus for future retrieval.

- `chunking.py` reads `data/docs` and `data/api_specs`, extracts normalized
  metadata, and produces deterministic overlapping chunks.
- `embeddings.py` provides production-style semantic vectors through a lazily
  loaded sentence-transformers model and deterministic no-network
  `local_hashing` vectors for development and CI smoke tests.
- `opensearch_client.py` creates the OpenSearch k-NN mapping and bulk-indexes
  chunk text, metadata, vector, and source path.
- `ingest.py` coordinates a complete ingestion run.

Configuration is supplied through `API_AGENT_*` environment variables. Start
OpenSearch through Docker Compose and run the CLI from the repository root:

```bash
uv run python scripts/ingest_docs.py
```

The local template selects `API_AGENT_EMBEDDING_BACKEND="local_hashing"` so an
ingestion smoke run does not need external model files. Select
`sentence_transformers` for semantic embeddings; that backend may download
the configured model files during its first use.
