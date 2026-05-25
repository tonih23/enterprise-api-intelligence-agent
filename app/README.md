# API Application Module

The `app` package owns the HTTP entrypoint for Enterprise API Intelligence
Agent.

- `main.py` defines the FastAPI application factory and ASGI `app`.
- `config.py` loads typed environment-based configuration.
- `health.py` exposes the process health endpoint and response schema.
- `rag/retriever.py` exposes `POST /rag/search` for keyword, vector, and
  hybrid retrieval over previously ingested synthetic documentation.
- `agent/api.py` exposes chat, local session history, and simulated approval
  endpoints backed by the deterministic LangGraph workflow.
- `observability/phoenix.py` optionally exports workflow spans to local
  Phoenix over OTLP/HTTP without making tracing a request dependency.

Run the API from the repository root with:

```bash
uv run uvicorn app.main:app --reload
```

The `/health` endpoint currently reports application process readiness and
configuration identity only. Agent session and approval metadata currently
uses an in-memory repository boundary; a future Postgres adapter can supply
durability without changing endpoint contracts.
