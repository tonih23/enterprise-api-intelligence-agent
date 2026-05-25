# Enterprise API Intelligence Agent

Enterprise API Intelligence Agent is an enterprise-style AI engineering
reference project inspired by MCP and API governance patterns. It will answer
questions about synthetic API documentation, expose controlled tools, and make
sensitive actions subject to human approval.

This initial implementation provides a typed FastAPI service foundation and a
health endpoint, plus local infrastructure through Docker Compose. It does not
use internal company data or call real APIs.

## Current Capabilities

- FastAPI application factory and executable ASGI app.
- Environment-based settings using the `API_AGENT_` prefix.
- `GET /health` endpoint with a typed response contract.
- Docker Compose services for the API, Postgres, OpenSearch, and Phoenix.
- Metadata-aware RAG ingestion for the fictional documentation corpus.
- Local MCP tools for synthetic API lookup, contract validation, and mock
  approval-gated change requests.
- Deterministic LangGraph orchestration for retrieval, MCP tool calls,
  clarification, and human approval gating.
- Agent HTTP endpoints for chat, local session history, and simulated approval
  of mock governed actions.
- Optional Phoenix-compatible traces for agent routing, retrieval, tools,
  approval decisions, and final response formatting.
- Deterministic synthetic evaluation suite for routes, evidence, tools,
  approval gating, and basic groundedness.
- Pytest and Ruff configuration managed through `pyproject.toml`.

The proposed end-to-end architecture and delivery sequence are documented in
[docs/architecture.md](docs/architecture.md) and
[docs/project_plan.md](docs/project_plan.md).

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.11, which `uv` can install and select from `.python-version`
- Docker with Docker Compose, when running the containerized stack

## Local Setup

Create local configuration and install the locked project dependencies:

```bash
cp .env.example .env
uv sync --dev
```

Run the API locally:

```bash
uv run uvicorn app.main:app --reload
```

The health endpoint is available at
[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health), and generated
API documentation is available at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Example response:

```json
{
  "status": "ok",
  "service": "Enterprise API Intelligence Agent",
  "version": "0.1.0",
  "environment": "local"
}
```

## Docker Compose

The local container stack runs:

| Service | Local URL or Port | Purpose |
| --- | --- | --- |
| `api` | [http://127.0.0.1:8000](http://127.0.0.1:8000) | FastAPI application |
| `postgres` | `127.0.0.1:5432` | Future conversation, audit, and evaluation persistence |
| `opensearch` | [http://127.0.0.1:9200](http://127.0.0.1:9200) | Hybrid retrieval index |
| `phoenix` | [http://127.0.0.1:6006](http://127.0.0.1:6006) | Trace and evaluation UI |

Copy the environment template before starting services. Docker Compose reads
these variables from `.env` for ports, versions, and local Postgres
credentials:

```bash
cp .env.example .env
docker compose up --build -d
```

Check the running API and infrastructure:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:9200
docker compose ps
```

Phoenix exposes its default web/HTTP collector port at `6006`; its gRPC
collector is also published at `4317`. Phoenix stores local state in the
`phoenix` schema of the Compose Postgres database.

Stop services while retaining local database and index volumes:

```bash
docker compose down
```

To discard local Compose data as well:

```bash
docker compose down --volumes
```

OpenSearch security is disabled in this Compose file solely for convenient
local development. Do not expose this local stack to an untrusted network or
reuse this setting for a hosted deployment.

## Document Ingestion

The synthetic source corpus under `data/docs` and `data/api_specs` can be
chunked, embedded, and indexed into OpenSearch. Each indexed record includes
its text, normalized metadata, embedding vector, stable chunk identifier, and
source path.

With OpenSearch running through Docker Compose:

```bash
uv run python scripts/ingest_docs.py
```

The `.env.example` configuration selects `local_hashing` for an easy local
smoke run:

- `sentence_transformers` creates real semantic embeddings. The documented
  semantic default is `BAAI/bge-large-en-v1.5`, a BGE large retrieval model.
  A Hugging Face model ID downloads model artifacts on first use unless they
  are already cached.
- `local_hashing` creates deterministic, normalized lexical feature-hash
  vectors with no network access or model download. It is only a local
  development and CI fallback, not a production semantic embedding approach.

Switch backends in `.env`. The semantic backend accepts either a Hugging Face
model ID or a previously downloaded local model folder:

```dotenv
# No-network local or CI ingestion
API_AGENT_EMBEDDING_BACKEND="local_hashing"

# Real semantic embedding ingestion from Hugging Face
API_AGENT_EMBEDDING_BACKEND="sentence_transformers"
API_AGENT_EMBEDDING_MODEL_NAME="BAAI/bge-large-en-v1.5"
API_AGENT_OPENSEARCH_INDEX_NAME="api_document_chunks_bge_large"

# Real semantic embedding ingestion from a pre-downloaded local folder
API_AGENT_EMBEDDING_BACKEND="sentence_transformers"
API_AGENT_EMBEDDING_MODEL_NAME="/absolute/path/to/bge-large-en-v1.5"
API_AGENT_OPENSEARCH_INDEX_NAME="api_document_chunks_bge_large"
```

When `API_AGENT_EMBEDDING_MODEL_NAME` points to an existing local directory,
the ingestion pipeline loads that directory in offline mode and does not
contact Hugging Face for model files. Keep local model directories out of
source control.

`local_hashing` produces 384-dimensional smoke-test vectors, while
`BAAI/bge-large-en-v1.5` produces 1024-dimensional semantic vectors. OpenSearch
vector dimensions cannot be changed in place: use a fresh index name when
switching from an index built with 384-dimensional vectors to BGE large.
Running ingestion again with the same compatible index replaces chunks with
matching stable identifiers rather than intentionally duplicating them.

In an enterprise deployment, the semantic backend would normally be connected
to an approved internal embedding endpoint or an internally hosted approved
model rather than depending on ad hoc workstation downloads.

## Document Search

After ingesting documents, query them through `POST /rag/search`. Requests
support `keyword`, `vector`, and `hybrid` modes plus optional exact filters for
`domain`, `system`, `api_name`, and `data_classification`.

Keyword/BM25 search is useful for exact endpoint paths, scopes, API names, and
error codes:

```bash
curl -X POST http://127.0.0.1:8000/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "POST /trial-interest-requests approval",
    "top_k": 3,
    "mode": "keyword",
    "filters": {"api_name": "clinical_trials_api"}
  }'
```

Hybrid search fuses BM25 candidates with vector candidates when a question
mixes technical identifiers with broader intent:

```bash
curl -X POST http://127.0.0.1:8000/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which trial action needs a human review before submission?",
    "top_k": 5,
    "mode": "hybrid",
    "filters": {"data_classification": "synthetic_internal"}
  }'
```

Vector and hybrid modes must use the embedding backend and vector dimensions
used to build the selected index. With the local template both use
`local_hashing`; a BGE semantic index must be queried with
`sentence_transformers` and its compatible index name.

## MCP Server

Run the local MCP stdio server with:

```bash
uv run python -m app.mcp_server.server
```

It exposes read-only catalogue search, synthetic API detail lookup, local
OpenAPI validation, and a mock change-request proposal tool. The mock change
request is marked as requiring human approval and does not create an external
record. Tool contracts and intended agent behavior are documented in
[docs/mcp_tools.md](docs/mcp_tools.md).

## Agent Flow

The local LangGraph workflow uses an explicit typed state and deterministic
router. A normal documentation question uses hybrid RAG; an explicit local
tool request calls the MCP service logic; a mock change-request action is
blocked in a pending human-approval state; and an ambiguous request asks for
clarification. The final response reports answer text, the route taken,
sources, tool calls, and approval status.

No external LLM or API key is required. The current router is selected with
`API_AGENT_ROUTER_BACKEND="deterministic"` and is isolated behind a node
interface so a configured LLM router can be added later. Module details are in
[app/agent/README.md](app/agent/README.md), with the graph diagram in
[docs/architecture.md](docs/architecture.md).

## Agent API

Submit a documentation question. Omitting `session_id` creates a local
session; reuse the returned value for later turns:

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message":"Which clinical trial operation needs approval?"}'
```

Use an explicit local command to select a read-only MCP tool:

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message":"Get API details for hcp_search_api","session_id":"demo-session"}'
```

A risky mock request is held pending approval and returns an `approval_id`
without executing the tool:

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message":"Create a change request for a synthetic API schema update.","session_id":"demo-session"}'
```

Approve that returned identifier to receive an approved mock object. This
does not write to any external change-management system:

```bash
curl -X POST http://127.0.0.1:8000/agent/approve/approval_REPLACE_WITH_RETURNED_ID
curl http://127.0.0.1:8000/agent/sessions/demo-session
```

For this initial local implementation, session and approval metadata is held
in memory behind a repository interface and resets when the API process
restarts. This keeps local execution simple while preserving a clean boundary
for a future Postgres-backed repository.

## Phoenix Tracing

Tracing is optional and disabled by default. Start the local Phoenix UI and
collector with its database dependency:

```bash
docker compose up -d postgres phoenix
```

Set these values in `.env` before running the API locally:

```dotenv
ENABLE_TRACING="true"
PHOENIX_COLLECTOR_ENDPOINT="http://127.0.0.1:6006/v1/traces"
```

Open Phoenix at
[http://127.0.0.1:6006](http://127.0.0.1:6006), then send requests to
`POST /agent/chat`. For a documentation question, expect spans for
`agent.run`, `agent.router`, `agent.rag`, and `agent.final_answer`. Local MCP
requests add `agent.mcp`; approval-gated requests add
`agent.human_approval`, and approval continuation adds
`agent.human_approval.decision`.

If tracing is disabled or the exporter cannot be configured, requests continue
normally. Span attributes contain workflow metadata only, not message text,
retrieved passages, or tool arguments. See
[docs/observability.md](docs/observability.md) for the AgentOps and governance
rationale.

## Evaluation

Run the 20-question synthetic regression baseline without OpenSearch, an
embedding-model download, Postgres, or an external LLM:

```bash
uv run python -m app.evals.run_evals
```

The command executes the existing LangGraph workflow with an offline
deterministic retriever over the checked-in fictional corpus, then writes a
local result artifact to `artifacts/evals/latest.json`. It reports
`route_accuracy`, `source_recall`, `tool_call_accuracy`,
`approval_precision`, and heuristic `answer_groundedness`.

This is a repeatable development baseline, not a production-quality benchmark.
When `ENABLE_TRACING=true`, evaluated graph runs use the same optional local
Phoenix trace path as agent API requests. Metric definitions and the future
Postgres persistence design are documented in
[docs/evaluation.md](docs/evaluation.md).

## Configuration

Configuration is read from environment variables or a local `.env` file.
`.env.example` contains non-sensitive defaults only.

| Variable | Purpose | Default |
| --- | --- | --- |
| `API_AGENT_APP_NAME` | Display name exposed by the service | `Enterprise API Intelligence Agent` |
| `API_AGENT_APP_VERSION` | Application version exposed by the service | `0.1.0` |
| `API_AGENT_ENVIRONMENT` | Runtime label: `local`, `test`, `staging`, or `production` | `local` |
| `API_AGENT_DEBUG` | Enable FastAPI debug behavior | `false` |
| `API_AGENT_LOG_LEVEL` | Intended application logging level | `INFO` |
| `API_AGENT_OPENSEARCH_URL` | OpenSearch endpoint used by ingestion | `http://127.0.0.1:9200` |
| `API_AGENT_OPENSEARCH_INDEX_NAME` | Chunk index destination | `api_document_chunks` |
| `API_AGENT_OPENSEARCH_VERIFY_CERTS` | Verify HTTPS certificates for OpenSearch | `false` |
| `API_AGENT_EMBEDDING_BACKEND` | `local_hashing` fallback or `sentence_transformers` semantic embeddings | `local_hashing` in `.env.example` |
| `API_AGENT_EMBEDDING_MODEL_NAME` | Hugging Face model ID or local folder used by `sentence_transformers` | `BAAI/bge-large-en-v1.5` |
| `API_AGENT_EMBEDDING_BATCH_SIZE` | Number of chunk texts embedded per batch | `32` |
| `API_AGENT_ROUTER_BACKEND` | Agent routing implementation; deterministic only in the local initial workflow | `deterministic` |
| `API_AGENT_RAG_CHUNK_SIZE` | Maximum chunk size in characters | `1000` |
| `API_AGENT_RAG_CHUNK_OVERLAP` | Repeated context between adjacent chunks | `150` |
| `ENABLE_TRACING` | Enable OTLP/HTTP trace export for agent workflow execution | `false` |
| `PHOENIX_COLLECTOR_ENDPOINT` | Phoenix HTTP trace collector used when tracing is enabled | `http://127.0.0.1:6006/v1/traces` |
| `API_PORT` | Published API port in Docker Compose | `8000` |
| `POSTGRES_*` | Local Postgres image, database, credentials, and port | See `.env.example` |
| `OPENSEARCH_*` | Local OpenSearch image, HTTP port, and JVM heap | See `.env.example` |
| `PHOENIX_*` | Local Phoenix image and collector/UI ports | See `.env.example` |

The Postgres password in `.env.example` is a local-development placeholder.
Replace it in `.env`; future credentials and connection values must likewise be
provided through environment configuration rather than source code.

## Development Checks

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
docker compose --env-file .env.example config --quiet
```

## Planned Modules

Future phases introduce durable Postgres implementations for the agent
repository and evaluation-result storage. Answer generation and broader
judging can later use configured models while preserving the deterministic
approval boundary. All corpus content and examples will remain synthetic.
