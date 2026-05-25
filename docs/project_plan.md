# Enterprise API Intelligence Agent: Project Plan

## Objective

Build a production-style, locally runnable reference application that answers questions about synthetic API documentation, invokes MCP tools through a governed LangGraph workflow, requires human approval for sensitive actions, and exposes operational evidence through tracing and evaluation.

The initial FastAPI and local-infrastructure foundation is implemented, along
with the first synthetic documentation corpus described below.

## Target Outcomes

- FastAPI endpoints for questions, workflow status, approvals, health, and evaluation triggers.
- LangGraph orchestration for retrieval, tool invocation, approval interruption, and response generation.
- MCP server with well-defined read-only and approval-required synthetic API tools.
- OpenSearch hybrid retrieval over fake API documentation artifacts with citations.
- Postgres records for conversations, traces of governed actions, approvals, and evaluation results.
- Phoenix instrumentation and a small repeatable evaluation dataset.
- Docker Compose development environment, tests, configuration documentation, and module READMEs.

## Proposed Repository Shape

```text
app/                    FastAPI entrypoint and API routes
agent/                  LangGraph state, nodes, policies, and prompts
retrieval/              Ingestion, chunking, embeddings, hybrid search
mcp_server/             MCP tools and tool policy metadata
persistence/            Postgres models and repositories
observability/          Phoenix tracing and evaluation integration
data/                   Synthetic docs, OpenAPI specs, Postman collections
evals/                  Evaluation datasets and runners
tests/                  Unit, integration, and API tests
docs/                   Architecture, operating, and design documentation
docker-compose.yml      Local service topology
.env.example            Safe environment variable template
```

Every major module should include a short README describing responsibility, interfaces, configuration, and test commands.

## Synthetic Dataset

The initial corpus uses a fictional Atlas Health Services sandbox scenario for
realistic retrieval, governance, and interview demonstration flows. It does
not represent a real organization or contain real company, healthcare
professional, patient, clinical trial, incident, or credential information.

| Artifact | Retrieval or evaluation purpose |
| --- | --- |
| `data/docs/fake_mulesoft_api_catalogue.md` | Catalogue lookup, endpoint discovery, scope questions, and approval classification |
| `data/api_specs/hcp_search_api.openapi.yaml` | Exact HCP search paths, schemas, errors, and read-only policy examples |
| `data/api_specs/clinical_trials_api.openapi.yaml` | Trial discovery operations and an explicit approval-required action |
| `data/api_specs/atlas_api_demo.postman_collection.json` | Example read requests and a governed write request with runtime token placeholder |
| `data/docs/api_governance_runbook.md` | Registration, classification, and human approval policy retrieval |
| `data/docs/incident_response_runbook.md` | Incident triage and policy-bypass response retrieval |
| `data/docs/teams_bot_architecture_notes.md` | Channel integration, grounded answers, and approval-card architecture |

All artifacts provide normalized metadata fields: `domain`, `owner`,
`data_classification`, `system`, `api_name`, and `version`. Markdown files use
YAML front matter; OpenAPI files use `info.x-agent-metadata`; and the Postman
collection uses `x-agent-metadata`. Reserved `.test` hostnames and invented
`*-SYN-*` identifiers make the synthetic boundary explicit.

## Delivery Phases

### Phase 0: Foundation And Conventions

Deliverables:

- Python 3.11 project packaging, dependency groups, `ruff`, `pytest`, optional `mypy`, and environment settings.
- `.env.example`, top-level README, module skeletons, and Docker Compose service definitions.
- CI-friendly commands for linting and tests.

Validation:

- Configuration tests confirm required settings fail clearly and no credentials are embedded.
- Compose configuration validates successfully.

### Phase 1: Synthetic Documentation Corpus

Deliverables:

- Invented API product documentation, fake OpenAPI specs, and a fake Postman collection.
- Corpus metadata conventions for API, version, document type, endpoint, and risk category.
- Ingestion fixtures suitable for deterministic tests.

Validation:

- Schema/fixture tests validate synthetic specifications and stable identifiers.
- Documentation states clearly that all APIs and examples are fictional.

### Phase 2: Hybrid Retrieval

Deliverables:

- Chunking and metadata extraction pipeline.
- OpenSearch lexical and vector index mappings.
- Hybrid search service with score fusion, filters, and cited retrieval output.

Validation:

- Unit tests cover chunking, metadata, fusion, and citation construction.
- Integration tests verify retrieval of exact endpoint terms and semantic questions from the synthetic corpus.

### Phase 3: MCP Tool Server

Deliverables:

- MCP server exposing documentation lookup tools and synthetic action-proposal tools.
- Tool metadata defining read-only versus approval-required behavior.
- Structured input and output schemas with audit-friendly error handling.

Validation:

- Contract tests cover schemas, tool discovery, read-only invocation, and rejection of unsafe inputs.

### Phase 4: LangGraph Orchestration And Approval

Deliverables:

- Typed workflow state and nodes for routing, retrieving, responding, calling tools, awaiting approval, resuming, and rejecting.
- Policy enforcement that sensitive tools cannot execute without an approval record.
- Model/provider integration configured through environment variables.

Validation:

- Graph tests cover answer, tool, approval, rejection, retry, and failure paths.
- Policy tests prove sensitive execution cannot bypass the approval node.

### Phase 5: FastAPI And Persistence

Deliverables:

- HTTP APIs for queries, conversations, pending approvals, approval decisions, and service readiness.
- Postgres persistence for conversation metadata, tool events, approval decisions, and evaluation runs.
- Correlation IDs, validation, consistent error responses, and redaction rules.

Validation:

- API tests validate status codes, schemas, approval lifecycle, and error cases.
- Repository integration tests validate durable workflow and audit state.

### Phase 6: Observability And Evaluation

Deliverables:

- Phoenix/OpenTelemetry tracing for API requests, graph nodes, retrieval, model calls, and MCP tools.
- Synthetic evaluation questions with expected sources and expected policy outcomes.
- Evaluation runner and persisted metrics for retrieval relevance, grounded answers, tool correctness, and approval compliance.

Validation:

- Tests confirm trace instrumentation is emitted without leaking secrets.
- Evaluation smoke runs produce stored and inspectable results.

### Phase 7: Local Operations And Documentation

Deliverables:

- Complete Docker Compose workflow for API, MCP, OpenSearch, Postgres, and Phoenix.
- Setup, ingestion, demo, troubleshooting, architecture, and security documentation.
- Module READMEs and example HTTP flows for both normal questions and approval-required actions.

Validation:

- Fresh-start smoke test brings up services, ingests synthetic data, answers a question with citations, and completes an approval flow.
- Full lint and test suite passes.

## Testing Strategy

| Test level | Primary purpose |
| --- | --- |
| Unit | Chunking, ranking/fusion, state transitions, policy decisions, schemas, redaction |
| Contract | MCP tool schemas and stable structured responses |
| Integration | OpenSearch retrieval, Postgres persistence, Phoenix instrumentation boundaries |
| API | FastAPI request/response and approval lifecycle behavior |
| Evaluation | Retrieval relevance, groundedness, tool selection, and policy compliance on synthetic cases |
| Smoke | Docker Compose end-to-end demonstration flow |

Tests should avoid network-dependent production systems and use deterministic synthetic fixtures wherever possible.

## Suggested Milestones

| Milestone | Demonstrable result | Phases |
| --- | --- | --- |
| Searchable knowledge base | A cited answer from synthetic API documentation | 0-2 |
| Governed agent workflow | An MCP action pauses for approval before execution | 3-5 |
| Operable reference system | Traceable, evaluated, documented Docker Compose demo | 6-7 |

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Retrieval appears accurate but answers are unsupported | Require citations and evaluate source relevance and groundedness |
| Tools are invoked without adequate control | Encode risk metadata and enforce approval in workflow and tests |
| Local stack becomes difficult to run | Start with minimal services, health checks, fixtures, and documented commands |
| Evaluation is subjective or too late | Define synthetic expected cases before expanding agent behavior |
| Sensitive configuration enters source control | Use environment settings, `.env.example`, redaction, and secret-focused reviews |

## Definition Of Done

- All content and examples remain synthetic and are presented as such.
- The service answers documented questions with cited retrieved evidence.
- MCP tools have validated contracts and sensitive actions require recorded human approval.
- Conversation, approval, and evaluation metadata are stored in Postgres.
- Phoenix exposes trace and evaluation evidence for key workflows.
- Docker Compose supports a documented local demonstration.
- Tests, linting, and documentation are current and passing for implemented capabilities.
