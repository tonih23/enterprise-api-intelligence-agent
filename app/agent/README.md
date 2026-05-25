# Agent Orchestration

This module contains the local LangGraph workflow for questions over the
fictional API corpus. It does not invoke an external LLM or a real operational
system.

## Flow

`AgentWorkflow` accepts a typed `AgentRequest`, then executes:

1. `request_guardrails`: blocks sensitive disclosures or real-system access
   requests and routes change actions into approval.
2. `router`: applies deterministic rules and selects retrieval, local MCP
   tooling, approval, or clarification.
3. `rag`: executes existing hybrid retrieval for documentation questions.
4. `tool_guardrails` and `mcp`: enforce tool policy, then invoke approved local
   MCP logic for synthetic lookups and local validation.
5. `human_approval`: records a pending request and prevents execution of
   `create_change_request_mock`.
6. `final_guardrails` and `final_answer`: require sufficient sourced evidence
   for factual answers and produce deterministic output with route, sources,
   tool calls, and approval status.

`create_agent_workflow` reads
`API_AGENT_ROUTER_BACKEND="deterministic"` to select the current routing
implementation. A later LLM-backed router can implement the same router node
contract and be selected through this configuration boundary; this module
does not require a model key today.

## HTTP And Storage

`app.agent.api` exposes `POST /agent/chat`, `GET /agent/sessions/{session_id}`,
and `POST /agent/approve/{approval_id}`. Chat requests accept only a user
message, optional session identifier, and retrieval `mode`/`top_k` controls;
documentation answers expose retrieved chunks for clients such as the local
Streamlit demo. Explicit commands such as `Get API details for hcp_search_api`
are mapped to local read-only MCP tools.

`repository.py` defines the session and approval persistence boundary. The
initial application uses `InMemoryAgentRepository` so local demos and tests
have no database bootstrap requirement. It records basic session metadata and
mock approval outcomes only for the application process lifetime. A Postgres
adapter can implement the same protocol when durable operational persistence
and migrations are added.

The graph accepts an optional tracer supplied by `app.observability.phoenix`.
With `ENABLE_TRACING=true`, each graph run and executed node emits local
Phoenix-compatible spans. With tracing disabled or unavailable, the same
workflow executes through a no-op tracer.

Guardrail policies and current limitations are documented in
`docs/guardrails.md`.
