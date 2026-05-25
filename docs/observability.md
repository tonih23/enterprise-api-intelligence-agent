# Observability And AgentOps

## Purpose

The project supports optional tracing to make agent control flow inspectable.
Phoenix provides a local/open-source demo view; LangSmith provides an optional
managed tracing view that is natural for LangGraph applications. The traced
workload uses fictional API documentation and mock governed actions only.

Tracing is disabled by default. When disabled, all instrumentation uses a
no-op tracer and the API behaves normally without either backend.

## Local Configuration

Set one backend explicitly:

```dotenv
API_AGENT_TRACING_BACKEND="none" # none, phoenix, or langsmith
```

### Phoenix

Start the local Phoenix collector and its Postgres dependency:

```bash
docker compose up -d postgres phoenix
```

Enable local Phoenix tracing when running the API locally:

```dotenv
API_AGENT_TRACING_BACKEND="phoenix"
PHOENIX_COLLECTOR_ENDPOINT="http://127.0.0.1:6006/v1/traces"
```

```bash
uv run uvicorn app.main:app --reload
```

Existing local configuration may continue to use `ENABLE_TRACING="true"`
without `API_AGENT_TRACING_BACKEND`; this legacy form selects Phoenix.

Open the Phoenix UI at
[http://127.0.0.1:6006](http://127.0.0.1:6006).

### LangSmith

LangSmith is an opt-in managed alternative, especially useful when explaining
LangGraph runs. Set credentials only in an uncommitted local `.env`:

```dotenv
API_AGENT_TRACING_BACKEND="langsmith"
LANGSMITH_PROJECT="enterprise-api-intelligence-agent"
# LANGSMITH_API_KEY=""  # Set only in your local uncommitted .env.
```

The LangSmith free tier is suitable for a small portfolio demo. An enterprise
deployment would require approved account, retention, and access-control
decisions.

## Span Model

An agent chat run can produce:

| Span | Purpose |
| --- | --- |
| `agent.run` | Parent span for one LangGraph execution |
| `guardrails.check` | Request, pre-tool, or final evidence checks, identified by `workflow_step` |
| `router.decide` | Deterministic route decision |
| `rag.retrieve` | Document retrieval and returned source count |
| `mcp.tool_call` | Local MCP tool dispatch, including an approved mock call |
| `approval.gate` | Pending gate or subsequent simulated approval decision |
| `llm.answer_synthesis` | Deterministic or optional Gemini final-wording boundary |
| `final_answer.compose` | Structured response assembly after guardrails |

Useful attributes include `route_taken`, `retrieval_mode`, `top_k`,
`number_of_sources`, `tool_name`, `approval_status`, `llm_provider`,
`llm_model`, and `answer_synthesis_mode`. Spans are marked with
`data_scope="synthetic_demo"`. Instrumentation intentionally does not attach
user messages, prompts, retrieved passages, OpenAPI content, tool arguments,
API keys, or credentials to exported spans.

## Demo Walkthrough

In Phoenix or LangSmith, open an `agent.run` trace after each sample question
and look for:

- A documentation question: `router.decide` followed by `rag.retrieve`, then
  `llm.answer_synthesis` and `final_answer.compose`.
- A local validation command: `mcp.tool_call` with its safe `tool_name`.
- A mock change request: `approval.gate` with
  `approval_status="pending_human_approval"` before any approved mock tool
  call.
- Optional Gemini mode: `llm_provider="gemini"` and the configured
  `llm_model`; deterministic fallback remains visible in
  `answer_synthesis_mode`.

## Failure Behavior

Observability is not a request-processing dependency. When tracing is off, no
exporter is configured. If Phoenix is unavailable, or LangSmith is selected
without `LANGSMITH_API_KEY` or cannot be initialized, the application logs a
warning and continues with no-op tracing. Trace export failures do not change
agent answers or approval controls.

## AgentOps And Governance

Agent systems need evidence about how a result was reached, not only whether
an endpoint returned successfully. Traces help reviewers examine:

- whether a query was routed to retrieval, a tool, clarification, or approval;
- whether retrieval occurred before evidence-based answer formatting;
- whether a mock sensitive action stopped at the approval boundary;
- whether an approved mock action occurred only after a recorded decision;
- which workflow paths and controls should be included in evaluations.

For enterprise AI governance, this provides a practical audit and evaluation
signal while preserving data-minimization principles. A production deployment
would add approved retention, access control, redaction review, and a governed
collector destination.
