# Observability And AgentOps

## Purpose

The project uses optional Phoenix-compatible OpenTelemetry tracing to make
agent control flow inspectable during local development. The traced workload
uses fictional API documentation and mock governed actions only.

Tracing is disabled by default. When disabled, all instrumentation uses a
no-op tracer and the API behaves normally without a Phoenix service.

## Local Configuration

Start the local Phoenix collector and its Postgres dependency:

```bash
docker compose up -d postgres phoenix
```

Enable tracing when running the API locally:

```dotenv
ENABLE_TRACING="true"
PHOENIX_COLLECTOR_ENDPOINT="http://127.0.0.1:6006/v1/traces"
```

```bash
uv run uvicorn app.main:app --reload
```

Alternatively, run the full Compose stack with `ENABLE_TRACING="true"` in
`.env`; the API container is configured to export to the local `phoenix`
service.

Open the Phoenix UI at
[http://127.0.0.1:6006](http://127.0.0.1:6006).

## Span Model

An agent chat run can produce:

| Span | Purpose |
| --- | --- |
| `agent.run` | Parent span for one LangGraph execution |
| `agent.router` | Deterministic route decision |
| `agent.rag` | Hybrid document retrieval call and result count |
| `agent.mcp` | Local MCP tool dispatch, including an approved mock call |
| `agent.human_approval` | Pending approval gate for a sensitive action |
| `agent.human_approval.decision` | Subsequent simulated approval endpoint decision |
| `agent.final_answer` | Deterministic response formatting |

The instrumentation records operational metadata such as selected route,
source count, tool name, and approval status. It intentionally does not attach
user messages, retrieved passages, OpenAPI content, or tool arguments to
exported spans.

## Failure Behavior

Phoenix is an observability dependency, not a request-processing dependency.
When tracing is off, no exporter is configured. If enabled tracing cannot be
configured, the application logs a warning and continues with a no-op tracer.
If a running collector becomes unavailable, OpenTelemetry export failures do
not change agent answers or approval controls.

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
