# Observability Module

`phoenix.py` owns optional tracer selection and the Phoenix
OpenTelemetry-compatible implementation. `langsmith.py` provides an optional
managed LangSmith adapter. Tracing is disabled by default.

Set `API_AGENT_TRACING_BACKEND="phoenix"` for local Phoenix export over
OTLP/HTTP, or `API_AGENT_TRACING_BACKEND="langsmith"` with a local
`LANGSMITH_API_KEY` for managed traces. Legacy `ENABLE_TRACING=true` still
selects Phoenix if no backend is explicitly configured.

Both adapters record route names, counts, tool names, approval status, and
answer-synthesis mode under readable spans such as `router.decide`,
`rag.retrieve`, `approval.gate`, and `llm.answer_synthesis`. They do not
attach user messages, prompts, retrieved text, tool argument payloads, or
credentials. Setup failure falls back to no-op tracing.
