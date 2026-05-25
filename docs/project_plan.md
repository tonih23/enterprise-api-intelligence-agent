# Project Plan

## Objective

Build an enterprise-style portfolio PoC that answers questions over synthetic
API documentation, exposes controlled local MCP-style tools, gates mock change
actions through approval, and makes behavior inspectable through tracing and
evaluation.

## Current Scope

| Capability | Status |
| --- | --- |
| FastAPI endpoints | Implemented: health, RAG search, agent chat, session history, simulated approval |
| Hybrid retrieval | Implemented: OpenSearch BM25, vector search, metadata filters, reciprocal-rank fusion |
| Embeddings | Implemented: `local_hashing` offline fallback and configurable `BAAI/bge-large-en-v1.5` semantic backend |
| MCP-style tools | Implemented: catalogue search, API details, local spec validation, mock change request |
| LangGraph workflow | Implemented: deterministic routing, retrieval, tools, approval, clarification, guardrails |
| Observability | Implemented: optional local Phoenix or managed LangSmith tracing |
| Evaluation | Implemented: 20-case offline synthetic baseline with local JSON results |
| Persistence | Partial: in-memory session/approval repository; Postgres application adapter is future work |
| Production security | Not implemented: authentication, authorization, tenant isolation, and governed external integrations |

## Synthetic Dataset

The checked-in corpus describes a fictional Atlas Health Services sandbox
scenario for retrieval and interview demonstrations. It does not represent a
real organization or contain real company, healthcare professional, patient,
trial, incident, or credential data.

| Artifact | Purpose |
| --- | --- |
| `data/docs/fake_mulesoft_api_catalogue.md` | API discovery, scopes, and approval classification |
| `data/api_specs/hcp_search_api.openapi.yaml` | Read-only endpoint and schema lookup |
| `data/api_specs/clinical_trials_api.openapi.yaml` | Trial operations and a mock approval-required action |
| `data/api_specs/atlas_api_demo.postman_collection.json` | Example calls with runtime token placeholder |
| `data/docs/api_governance_runbook.md` | Governance and human approval guidance |
| `data/docs/incident_response_runbook.md` | Synthetic incident response guidance |
| `data/docs/teams_bot_architecture_notes.md` | Fictional channel integration design notes |

Each artifact provides `domain`, `owner`, `data_classification`, `system`,
`api_name`, and `version` metadata plus `synthetic: true`. Hosts use reserved
`.test` names and identifiers are invented.

## Delivery Priorities

### Delivered Local Vertical Slice

- Ingest synthetic content into OpenSearch with an offline-safe default.
- Retrieve evidence through HTTP and the agent workflow.
- Execute read-only local tools and hold a mock change request for approval.
- Trace workflow metadata optionally and run deterministic regression evals.
- Keep tests independent of model downloads and external services.

### Next Production-Oriented Increments

- Add a Postgres repository adapter for sessions, approvals, audit events, and
  evaluation results.
- Add authentication, authorization, tenant isolation, rate limiting, and
  secrets management.
- Integrate an approved approval workflow and approved embedding/model
  service.
- Add CI/CD controls, monitoring, security review, and model-governance
  processes.

Deployment alternatives and the production gap are described in
[production_readiness.md](production_readiness.md).

## Verification Strategy

| Check | Purpose |
| --- | --- |
| Unit/API tests | Schemas, routing, tools, guardrails, approval, and HTTP behavior |
| Corpus tests | Synthetic labeling, metadata, reserved hosts, and approval flags |
| Offline evaluations | Stable route, source, tool, approval, and groundedness regression signals |
| Ruff | Consistent Python formatting and static lint checks |
| Docker Compose smoke run | Local API, OpenSearch, Phoenix, and Postgres wiring |

Tests and offline evaluations avoid external APIs, real systems, and model
downloads. Semantic BGE retrieval is an opt-in local demonstration or a
deployment concern for an approved hosted model or embedding endpoint.
