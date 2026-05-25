---
document_id: "runbook-governance-001"
document_type: "governance_runbook"
title: "Fictional API Governance Runbook"
synthetic: true
domain: "api_governance"
owner: "fictional_api_governance_council"
data_classification: "synthetic_internal"
system: "atlas_governance_workflow_sandbox"
api_name: "governance_controls"
version: "1.0.0"
---

# Fictional API Governance Runbook

> This runbook is entirely synthetic. It models review controls for an
> interview demonstration and is not an organizational policy.

## Purpose

This runbook defines lightweight governance controls for fictional APIs
published in the Atlas sandbox catalogue. It gives the agent clear boundaries
between documentation lookup, action proposals, and actions that require
human authorization.

## API Registration Checklist

An API owner supplies:

- API name, owning team, business domain, system, classification, and semantic
  version.
- An OpenAPI specification with operation identifiers, scopes, response
  schemas, error formats, and example values that contain no real data.
- A support contact alias, lifecycle state, rate-limit guidance, and an
  incident runbook link.
- A Postman collection that references environment variables for tokens and
  base URLs rather than embedding secrets.

The fictional API Governance Council records the review outcome as
`draft`, `approved_for_sandbox`, `changes_requested`, or `retired`.

## Risk And Approval Matrix

| Requested capability | Example | Agent behavior | Human approval |
| --- | --- | --- | --- |
| Read published documentation | Explain the HCP Search endpoint | Retrieve and answer with citations | Not required |
| Read synthetic API resource | Search invented HCP summaries | Call read-only tool and log trace | Not required |
| Propose consumer subscription | Draft an application-access request | Create pending proposal | Required |
| Submit trial interest request | Send synthetic follow-up request | Create pending proposal | Required |
| Change API lifecycle state | Retire an API version | Reject autonomous execution; escalate | Required |

## Approval Workflow

1. The agent identifies an approval-required tool from structured tool policy.
2. It records a pending action containing requester, API name, version,
   proposed inputs, risk level, and correlation ID.
3. A reviewer sees the proposed action and either approves or rejects it.
4. Only an approved action may be resumed for execution in the sandbox.
5. The system records reviewer decision metadata, tool result, timestamp, and
   trace identifier in the audit log.

No prompt instruction can override this workflow control.

## Classification Guidance

| Classification | Meaning In This Project | Example |
| --- | --- | --- |
| `synthetic_public` | Invented information suitable for demos | API description |
| `synthetic_internal` | Invented operational material used in testing | Runbook or lifecycle status |
| `synthetic_restricted` | Invented records shaped like controlled data | Fictional HCP profile |

Synthetic classifications demonstrate routing policy only; they do not
represent actual regulated information.

## Version And Retirement Policy

- API versions follow semantic versioning in the sandbox catalogue.
- Breaking schema or authorization changes require a new major version.
- Retired versions remain searchable for audit context but are marked as
  unavailable for new subscriptions.
- Evaluation questions should identify version mismatches and retired
  endpoints.

## Audit Evidence

For an approval-required tool call, capture the API name and version,
classification, selected tool, redacted proposed arguments, decision state,
reviewer role, correlation ID, and Phoenix trace identifier. Access tokens,
client secrets, and raw credentials must never appear in the evidence record.
