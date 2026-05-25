# Agent Guardrails

## Purpose

The agent operates only on synthetic API documentation and local mock actions.
Guardrails provide deterministic controls around that boundary before any
future model-based routing or answer generation is introduced.

## Enforced Controls

| Control | Behavior |
| --- | --- |
| Restricted disclosure | Requests to reveal secrets, credentials, tokens, or private data are blocked. |
| Real-system access | Requests to access real company or production systems are blocked. |
| Change-management actions | Destructive or change-oriented requests are routed to pending human approval. |
| Sensitive tools | `create_change_request_mock` cannot run through the graph without approval. |
| Sourced factual answers | Documentation answers require returned source references. |
| Weak retrieval | No results or retrieval scores below the local confidence floor result in a clarification prompt. |
| API-name integrity | A requested API must be backed by a local synthetic specification; an unknown name is not represented as valid. |
| Synthetic boundary | User-facing grounded answers and refusal/approval responses identify that this is a synthetic demonstration. |

## Workflow Placement

The LangGraph workflow runs guardrails at three boundaries:

1. `request_guardrails` runs before routing. It rejects prohibited disclosure
   or real-system access requests and diverts change actions to approval.
2. `tool_guardrails` runs before read-only MCP tool execution. It rechecks
   restrictions and ensures sensitive tools cannot execute directly.
3. `final_guardrails` runs before answer formatting. It checks that factual
   documentation answers have sufficient synthetic evidence and converts
   unsupported results into clarification prompts.

The separate approval HTTP endpoint executes only the local mock
change-request tool after a recorded approval decision. It still does not
create or modify any real external object.

## Low-Confidence Rule

The current implementation uses a simple deterministic rule:

- an answer routed through document retrieval must contain at least one source;
- its highest returned score must be at least `0.01`;
- sourced read-tool answers must include a source document.

This threshold is a local safety baseline, not a calibrated confidence model.
Production deployments would calibrate retrieval thresholds per index and
model and evaluate abstention quality on a maintained benchmark.

## Limitations

- Pattern matching cannot detect every sensitive intent or all prompt
  paraphrases. It is a transparent baseline, not a complete data-loss
  prevention system.
- The application has no authentication or authorization layer yet; a
  production approval flow requires identity, role checks, and audit
  persistence.
- Unknown API names are checked when the local metadata tool is used. General
  retrieval answers remain constrained by returned synthetic sources.
- Guardrails do not make synthetic records suitable for production use or
  imply access to an enterprise system.

These controls should be combined in a real deployment with authenticated
users, authorization, redaction, approved tool policies, durable audit logs,
monitoring, and human review.
