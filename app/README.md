# API Application Module

The `app` package owns the HTTP entrypoint for Enterprise API Intelligence
Agent.

- `main.py` defines the FastAPI application factory and ASGI `app`.
- `config.py` loads typed environment-based configuration.
- `health.py` exposes the process health endpoint and response schema.
- `rag/retriever.py` exposes `POST /rag/search` for keyword, vector, and
  hybrid retrieval over previously ingested synthetic documentation.

Run the API from the repository root with:

```bash
uv run uvicorn app.main:app --reload
```

The `/health` endpoint currently reports application process readiness and
configuration identity only. Health checks for future services such as
OpenSearch or Postgres should be added when application readiness depends on
those integrations.
