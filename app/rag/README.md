# RAG Module

The `app.rag` package prepares and retrieves the fictional API corpus.

- `chunking.py` reads `data/docs` and `data/api_specs`, extracts normalized
  metadata, and produces deterministic overlapping chunks.
- `embeddings.py` provides real semantic vectors through a lazily
  loaded sentence-transformers model and deterministic no-network
  `local_hashing` vectors for development and CI smoke tests.
- `opensearch_client.py` creates the OpenSearch k-NN mapping and bulk-indexes
  chunk text, metadata, vector, and source path.
- `ingest.py` coordinates a complete ingestion run.
- `schemas.py` defines the public search request, filters, and result shape.
- `retriever.py` provides BM25 keyword search, k-NN vector search, and hybrid
  retrieval using reciprocal rank fusion.

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

## Retrieval Modes

API documentation needs both exact and conceptual retrieval behavior:

- **Keyword (`keyword`)** uses OpenSearch BM25 scoring. It is strongest for
  exact technical strings such as `POST /trial-interest-requests`,
  `X-Correlation-Id`, HTTP error codes, OAuth scopes, API names, and version
  numbers.
- **Vector (`vector`)** embeds the question and runs k-nearest-neighbor
  search. With `sentence_transformers`, it helps with semantic questions where
  the wording differs from the documentation. With `local_hashing`, it is a
  deterministic local or CI smoke path only.
- **Hybrid (`hybrid`)** runs both strategies and combines their ranked results
  with reciprocal rank fusion. This keeps technical terms and API identifiers
  prominent while still recovering contextually relevant guidance.

All retrieval modes support exact filters for `domain`, `system`, `api_name`,
and `data_classification`. After ingestion, access retrieval through:

```http
POST /rag/search
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which endpoint submits trial interest after approval?",
    "top_k": 5,
    "mode": "hybrid",
    "filters": {"api_name": "clinical_trials_api"}
  }'
```
