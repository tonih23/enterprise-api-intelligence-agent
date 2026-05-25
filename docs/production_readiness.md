# Production Readiness

## Positioning

Enterprise API Intelligence Agent is an enterprise-style portfolio PoC
inspired by API governance, MCP/tooling, and regulated AI patterns. It uses
synthetic data and local mock actions only; it is not a production service or
an internal company system.

## Current Local Architecture

| Component | Current Role |
| --- | --- |
| FastAPI | HTTP endpoints for health, retrieval, chat, sessions, and simulated approval |
| Docker Compose | Reproducible local service startup |
| OpenSearch | Hybrid keyword and vector retrieval index |
| Postgres | Local Phoenix backing database; available for future operational persistence |
| Phoenix | Optional local trace inspection and evaluation visibility |
| Local MCP-style tools | Synthetic catalogue lookup, spec validation, and mock change request |
| Local BGE embeddings | `BAAI/bge-large-en-v1.5` semantic option via model ID or local model folder |
| `local_hashing` | Non-semantic, no-network fallback for smoke tests and CI |

Session and approval metadata currently use a local repository implementation,
and evaluation results are written to local JSON.

## Cloud-Ready Target Architecture

| Capability | Practical Target Options |
| --- | --- |
| API hosting | ECS/Fargate, Azure App Service, or Cloud Run |
| Operational database | Managed Postgres |
| Retrieval service | Managed OpenSearch, Elastic, or Azure AI Search |
| Embeddings | Approved internal embedding endpoint, Azure OpenAI, Cohere Embed via Bedrock, or internally hosted BGE/E5/GTE |
| Observability | Centralized logging and tracing with controlled retention and redaction |
| Secrets | AWS Secrets Manager or Azure Key Vault |

## Required Before Production

- Authentication and authorization.
- Rate limiting and tenant isolation.
- Durable audit, session, approval, and evaluation persistence.
- CI/CD with tested deployment and rollback controls.
- Security review, threat modeling, and data-retention policy.
- Model governance and approved embedding/model sourcing.
- Monitoring, alerts, incident response, and evaluation quality gates.
- Real approval workflow integration for any controlled action.
