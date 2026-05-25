# Local Demo UI

The Streamlit app is a thin local client for the FastAPI agent endpoints. It
does not implement retrieval, routing, tools, or approval policy itself. All
data and returned actions remain synthetic.

## Start The Demo

Start local infrastructure and ingest the synthetic corpus:

```bash
cp .env.example .env
docker compose up -d opensearch
uv run python scripts/ingest_docs.py
```

Start the FastAPI backend and Streamlit UI in separate terminals:

```bash
uv run uvicorn app.main:app --reload
uv run streamlit run demo/streamlit_app.py
```

Open the Streamlit URL shown in the terminal, normally
`http://localhost:8501`. The UI sends questions to the local
`POST /agent/chat` endpoint and can continue an approval-gated mock action
through `POST /agent/approve/{approval_id}`.

Phoenix tracing remains optional; start `postgres` and `phoenix` through
Docker Compose and set `ENABLE_TRACING="true"` when trace visualization is
useful for the demo.

## Suggested Demo Questions

1. `Which API should I use to search for HCP candidates?`
2. `Which action requires human approval?`
3. `Validate the HCP Search OpenAPI spec.`

The third question exercises local validation of the fictional HCP Search
OpenAPI artifact. An approval shown in the UI is a simulated local control
flow and never executes an external change.

## Embedding Modes

The backend, not Streamlit, selects the embedding implementation. The sidebar
selection explains which local configuration to use:

- `local_hashing` is a deterministic, non-semantic, no-network fallback for
  smoke tests and CI.
- `sentence_transformers` with `BAAI/bge-large-en-v1.5` provides real
  semantic embeddings from a model ID or a pre-downloaded local folder.

For local BGE embeddings, configure `.env` before ingestion and backend
startup:

```dotenv
API_AGENT_EMBEDDING_BACKEND="sentence_transformers"
API_AGENT_EMBEDDING_MODEL_NAME="/absolute/path/to/bge-large-en-v1.5"
API_AGENT_OPENSEARCH_INDEX_NAME="api_document_chunks_bge_large"
```

BGE large uses 1024-dimensional vectors; create a fresh index rather than
reusing an index built with the 384-dimensional `local_hashing` fallback.
