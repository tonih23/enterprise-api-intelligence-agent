---
document_id: "runbook-incident-001"
document_type: "incident_response_runbook"
title: "Fictional API Incident Response Runbook"
synthetic: true
domain: "service_reliability"
owner: "fictional_platform_operations_team"
data_classification: "synthetic_internal"
system: "atlas_api_operations_sandbox"
api_name: "api_incident_response"
version: "1.0.0"
---

# Fictional API Incident Response Runbook

> Synthetic operational scenario only. Incident IDs, responders, systems, and
> customer impact are fictional and exist for retrieval and evaluation tests.

## Scope

This runbook covers degraded sandbox behavior for `hcp_search_api` and
`clinical_trials_api`, as well as failures in the documentation retrieval path
used by the API intelligence agent.

## Severity Guide

| Severity | Synthetic scenario | Initial response target |
| --- | --- | --- |
| `SEV-1` | Sandbox write action executed without required approval | Immediate containment and audit review |
| `SEV-2` | Read endpoints return sustained `5xx` errors or retrieval provides a retired API version | Triage within 30 minutes |
| `SEV-3` | Rate-limit spikes, stale catalogue display, or delayed trace export | Review during support window |

## Example Incident

- **Incident ID:** `INC-SYN-0042`
- **Affected API:** `clinical_trials_api` version `2.1.0`
- **Symptom:** Queries for trial sites intermittently return `503` in the
  fictional sandbox.
- **Classification:** `synthetic_internal`
- **Correlation ID:** `corr-syn-8f19c2`

No real patients, professionals, studies, users, or services are affected by
this invented scenario.

## Triage Procedure

1. Confirm the API name, version, environment, correlation ID, and time
   window; do not paste bearer tokens into incident notes.
2. Check API health, OpenSearch status, Postgres status, and Phoenix traces
   for the affected fictional workflow.
3. Determine whether the failure affects documentation retrieval, read-only
   API invocation, or an approval-required action.
4. For unexpected tool execution or suspected approval bypass, declare
   `SEV-1`, suspend sensitive tools, and preserve audit events.
5. Record containment, evidence links, decision owner, and recovery outcome.

## Agent-Safe Actions

| Action | Allowed automatically? | Reason |
| --- | --- | --- |
| Retrieve this runbook and summarize triage steps | Yes | Read-only evidence retrieval |
| Look up a correlation ID in synthetic trace metadata | Yes | Read-only observation |
| Disable a sensitive tool or change a lifecycle state | No | Operational change requires approval |
| Replay a failed write proposal | No | May create a side effect |

## Communications Template

```text
[SYNTHETIC SANDBOX INCIDENT] INC-SYN-0042 - SEV-2
Affected capability: clinical_trials_api v2.1.0 trial-site lookup
Observed behavior: intermittent HTTP 503 responses
Data involved: fictional examples only
Next update: after trace and service-health review
```

## Closure Checklist

- Confirm the sandbox API or retrieval index returned to healthy status.
- Associate the resolution with the trace ID and synthetic correlation ID.
- Verify no approval-required tool executed outside an approved state.
- Create an evaluation case if the incident exposed a retrieval or policy gap.
