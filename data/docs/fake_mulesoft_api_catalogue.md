---
document_id: "catalogue-doc-001"
document_type: "api_catalogue"
title: "Fictional MuleSoft API Catalogue"
synthetic: true
domain: "api_enablement"
owner: "fictional_api_platform_team"
data_classification: "synthetic_internal"
system: "atlas_mulesoft_exchange_sandbox"
api_name: "enterprise_api_catalogue"
version: "1.0.0"
---

# Fictional MuleSoft API Catalogue

> Synthetic interview demonstration artifact. The organization, APIs, owners,
> consumers, identifiers, and endpoints in this catalogue are invented.

## Catalogue Purpose

Atlas Health Services is a fictional organization used to demonstrate how an
API intelligence agent can find reusable interfaces, explain access controls,
and enforce governance workflows. This page represents a curated catalogue
view that might be published through a MuleSoft developer portal in a sandbox.

## Published APIs

| API | Domain | Lifecycle | Version | Owner | Classification | Sandbox Base URL |
| --- | --- | --- | --- | --- | --- | --- |
| HCP Search API | Healthcare professional engagement | Active | `1.2.0` | Provider Experience Platform | Synthetic restricted | `https://sandbox.api.atlas-health.test/hcp-search/v1` |
| Clinical Trials API | Research operations | Active | `2.1.0` | Trial Discovery Platform | Synthetic internal | `https://sandbox.api.atlas-health.test/clinical-trials/v2` |

## HCP Search API

- **API name:** `hcp_search_api`
- **System:** `atlas_hcp_directory_sandbox`
- **Primary use case:** Locate invented healthcare professional directory
  profiles by name, specialty, or country for demonstration workflows.

Key operations:

| Method and path | Description | Required scope | Approval |
| --- | --- | --- | --- |
| `GET /healthcare-professionals` | Search synthetic HCP summaries | `hcp.read` | Not required |
| `GET /healthcare-professionals/{hcp_id}` | Read a synthetic profile | `hcp.read` | Not required |

Design notes:

- Results contain fictional professional contact and specialty metadata only.
- Client applications should use pagination and propagate `X-Correlation-Id`.
- A `429` response indicates the sandbox rate limit was reached; use the
  `Retry-After` header rather than immediately retrying.

## Clinical Trials API

- **API name:** `clinical_trials_api`
- **System:** `atlas_trial_registry_sandbox`
- **Primary use case:** Find fictional study summaries and sites and create a
  governed interest-request proposal.

Key operations:

| Method and path | Description | Required scope | Approval |
| --- | --- | --- | --- |
| `GET /trials` | Search synthetic trial summaries | `trials.read` | Not required |
| `GET /trials/{trial_id}` | Retrieve synthetic trial detail | `trials.read` | Not required |
| `GET /trials/{trial_id}/sites` | List invented participating sites | `trials.read` | Not required |
| `POST /trial-interest-requests` | Propose follow-up from a fictional HCP | `trials.interest.write` | Required |

The `POST` operation is intentionally classified as approval-required so an
agent may draft the action but cannot execute it without a recorded human
decision.

## Access And Subscription Pattern

1. Locate the API and version in the catalogue.
2. Request an application contract for a fictional sandbox consumer.
3. Receive OAuth client credentials through a secret-managed process; no
   credential value is placed in documentation or prompts.
4. Send a bearer token with the required scope and an `X-Correlation-Id`.
5. Raise changes or elevated-access requests through the API governance
   runbook.

## Search Questions Supported By This Artifact

- Which API supports searching for a cardiologist in Spain?
- What scope is required to list trial sites?
- Which action needs human approval?
- Where should a client look when sandbox requests start returning `429`?
