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
