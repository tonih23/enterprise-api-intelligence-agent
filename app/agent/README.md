# Agent Orchestration

This module contains the local LangGraph workflow for questions over the
fictional API corpus. It does not invoke an external LLM or a real operational
system.

## Flow

`AgentWorkflow` accepts a typed `AgentRequest`, then executes:

1. `router`: applies deterministic rules and selects retrieval, local MCP
   tooling, approval, or clarification.
2. `rag`: executes existing hybrid retrieval for documentation questions.
3. `mcp`: invokes approved local MCP tool logic for synthetic lookups and
   local validation.
4. `human_approval`: records a pending request and prevents execution of
   `create_change_request_mock`.
5. `final_answer`: produces deterministic text together with sources, tool
   calls, route, and approval status.

`create_agent_workflow` reads
`API_AGENT_ROUTER_BACKEND="deterministic"` to select the current routing
implementation. A later LLM-backed router can implement the same router node
contract and be selected through this configuration boundary; this module
does not require a model key today.

## HTTP And Storage

`app.agent.api` exposes `POST /agent/chat`, `GET /agent/sessions/{session_id}`,
and `POST /agent/approve/{approval_id}`. Chat requests accept only a user
message and optional session identifier; explicit commands such as
`Get API details for hcp_search_api` are mapped to local read-only MCP tools.

`repository.py` defines the session and approval persistence boundary. The
initial application uses `InMemoryAgentRepository` so local demos and tests
have no database bootstrap requirement. It records basic session metadata and
mock approval outcomes only for the application process lifetime. A Postgres
adapter can implement the same protocol when durable operational persistence
and migrations are added.
