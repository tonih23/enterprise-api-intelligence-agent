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
ingestion smoke run does not need external model files. It creates
384-dimensional lexical feature-hash vectors only and is not a semantic
embedding strategy for production.

Select `sentence_transformers` for real semantic embeddings. The documented
default is `BAAI/bge-large-en-v1.5`, which produces 1024-dimensional vectors:

```dotenv
API_AGENT_EMBEDDING_BACKEND="sentence_transformers"
API_AGENT_EMBEDDING_MODEL_NAME="BAAI/bge-large-en-v1.5"
API_AGENT_OPENSEARCH_INDEX_NAME="api_document_chunks_bge_large"
```

`API_AGENT_EMBEDDING_MODEL_NAME` also accepts a pre-downloaded local model
directory. Existing folders are loaded with `local_files_only=True`, so this
mode does not make a Hugging Face model download request:

```dotenv
API_AGENT_EMBEDDING_BACKEND="sentence_transformers"
API_AGENT_EMBEDDING_MODEL_NAME="/absolute/path/to/bge-large-en-v1.5"
API_AGENT_OPENSEARCH_INDEX_NAME="api_document_chunks_bge_large"
```

Use a fresh OpenSearch index when switching from `local_hashing` to BGE large:
an index mapped for 384-dimensional local fallback vectors is incompatible
with 1024-dimensional BGE embeddings. Enterprise deployments would normally
use an approved internal embedding endpoint or an internally hosted approved
model.
