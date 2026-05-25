# Enterprise API Intelligence Agent

## Project Overview

Enterprise API Intelligence Agent is an enterprise-style portfolio proof of
concept inspired by API governance, MCP/tooling, and regulated AI patterns. It
answers questions over synthetic API documentation, exposes controlled local
tools, and pauses mock change actions for human approval.

The project uses fictional API specifications and runbooks only. It does not
contain internal company data or connect to real enterprise systems.

## What Problem It Solves

API consumers need answers that combine exact technical details, such as paths
and API names, with broader policy and operational context. This project
demonstrates how an agent can:

- retrieve grounded evidence from API documentation;
- call structured tools without hiding side effects;
- enforce approval and guardrail decisions; and
- expose traces and repeatable evaluations for engineering review.

## Architecture

```mermaid
flowchart LR
    User["User"] --> API["FastAPI<br/>/rag/search and /agent/chat"]
    API --> Graph["LangGraph<br/>deterministic workflow"]
    Graph --> Policy["Guardrails and<br/>human approval"]
    Graph --> RAG["Hybrid RAG<br/>BM25 + vector"]
    Graph --> Tools["Local MCP-style tools"]
    Docs["Synthetic docs<br/>and API specs"] --> Ingest["Chunking and<br/>embeddings"]
    Ingest --> Search["OpenSearch"]
    RAG --> Search
    Graph -. "optional traces" .-> Phoenix["Phoenix"]
    Phoenix --> Postgres["Postgres<br/>local trace storage"]
    Evals["Synthetic eval suite"] --> Graph
```

The API currently keeps session and approval metadata in a local repository
implementation; a Postgres-backed operational repository is a production
extension.

## Tech Stack

| Area | Technology |
| --- | --- |
| API service | Python 3.11, FastAPI, Pydantic |
| Agent workflow | LangGraph with deterministic routing |
| Tool interface | MCP Python SDK with local synthetic tools |
| Retrieval | OpenSearch hybrid keyword/vector search |
| Embeddings | Sentence Transformers or deterministic `local_hashing` fallback |
| Local infrastructure | Docker Compose, Postgres, Phoenix |
| Quality | pytest, Ruff, synthetic evaluation suite |

## Key AI Engineering Features

| Feature | Purpose |
| --- | --- |
| Hybrid RAG | Combines BM25 exact matching with vector retrieval for technical and semantic questions. |
| MCP-style tools | Provides typed local capabilities for catalogue search, spec validation, and mock changes. |
| LangGraph orchestration | Makes routing, retrieval, tool execution, approval, and final response steps testable. |
| Human approval | Prevents approval-gated mock change requests from executing immediately. |
| Guardrails | Rejects restricted requests and requires sources for documentation-based factual answers. |
| Tracing | Optionally exports workflow spans to local Phoenix for AgentOps inspection. |
| Evaluations | Runs a 20-question synthetic baseline for route, source, tool, approval, and groundedness metrics. |

## How To Run Locally

Requirements: [uv](https://docs.astral.sh/uv/), Python 3.11, and Docker
Compose for the local infrastructure stack.

```bash
cp .env.example .env
uv sync --dev
docker compose up --build -d
curl http://127.0.0.1:8000/health
uv run pytest
```

Local services:

| Service | Address |
| --- | --- |
| FastAPI and Swagger UI | `http://127.0.0.1:8000` and `http://127.0.0.1:8000/docs` |
| OpenSearch | `http://127.0.0.1:9200` |
| Postgres | `127.0.0.1:5432` |
| Phoenix | `http://127.0.0.1:6006` |

To run the API process directly while infrastructure remains containerized:

```bash
uv run uvicorn app.main:app --reload
```

Tracing is optional. Set `ENABLE_TRACING="true"` in `.env`, open Phoenix at
`http://127.0.0.1:6006`, and submit agent requests to inspect route,
retrieval, tool, approval, guardrail, and final-answer spans. Details are in
[docs/observability.md](docs/observability.md).

## How To Ingest Synthetic Docs

With OpenSearch running:

```bash
uv run python scripts/ingest_docs.py
```

The ingestion pipeline reads fictional documents from `data/docs` and
`data/api_specs`, extracts metadata, chunks text, generates embeddings, and
indexes the chunks in OpenSearch.

## How To Query `/rag/search`

Hybrid search is the default interview-friendly example because it combines
technical identifiers with intent:

```bash
curl -X POST http://127.0.0.1:8000/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which trial action needs human review before submission?",
    "top_k": 5,
    "mode": "hybrid",
    "filters": {"data_classification": "synthetic_internal"}
  }'
```

Supported modes are `keyword`, `vector`, and `hybrid`. Optional filters are
`domain`, `system`, `api_name`, and `data_classification`.

## How To Query `/agent/chat`

Ask a grounded documentation question:

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message":"Which clinical trial operation needs approval?"}'
```

Requesting a mock governed action returns an `approval_id` without executing
the tool:

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message":"Create a change request for a synthetic API schema update.","session_id":"demo-session"}'

curl -X POST http://127.0.0.1:8000/agent/approve/approval_REPLACE_WITH_RETURNED_ID
curl http://127.0.0.1:8000/agent/sessions/demo-session
```

Approval returns a synthetic mock result only; it does not create a record in
an external change-management system. Tool contracts are documented in
[docs/mcp_tools.md](docs/mcp_tools.md).

## How To Run Evals

```bash
uv run python -m app.evals.run_evals
```

The offline synthetic baseline writes `artifacts/evals/latest.json` and
reports `route_accuracy`, `source_recall`, `tool_call_accuracy`,
`approval_precision`, and heuristic `answer_groundedness`. See
[docs/evaluation.md](docs/evaluation.md).

## Local Embeddings

| Backend | Intended use | Dimensions |
| --- | --- | --- |
| `local_hashing` | Deterministic, no-network, non-semantic fallback for local smoke tests and CI | 384 |
| `sentence_transformers` with `BAAI/bge-large-en-v1.5` | Real local semantic embedding model for realistic retrieval demonstrations | 1024 |

The checked-in local default is safe for offline execution:

```dotenv
API_AGENT_EMBEDDING_BACKEND="local_hashing"
API_AGENT_EMBEDDING_MODEL_NAME="BAAI/bge-large-en-v1.5"
```

Enable real semantic embeddings from a Hugging Face model ID or a
pre-downloaded local folder:

```dotenv
API_AGENT_EMBEDDING_BACKEND="sentence_transformers"
API_AGENT_EMBEDDING_MODEL_NAME="/absolute/path/to/bge-large-en-v1.5"
API_AGENT_OPENSEARCH_INDEX_NAME="api_document_chunks_bge_large"
```

Use a fresh OpenSearch index when switching from 384-dimensional
`local_hashing` vectors to 1024-dimensional BGE large vectors. Enterprise
deployments would typically use an approved internal embedding endpoint or an
internally hosted approved model.

## Production And Cloud Readiness

This is a local portfolio PoC with production-shaped boundaries: typed APIs,
retrieval metadata, workflow controls, optional traces, and evaluations.
Production deployment would require managed infrastructure, durable
operational storage, security controls, and an integrated approval workflow.
See [docs/production_readiness.md](docs/production_readiness.md).

## Limitations

- The corpus and all tool results are synthetic; no real enterprise access is provided.
- Routing and response generation are deterministic; no external LLM is called.
- Session and approval records are local in-memory data, and eval output is local JSON.
- Guardrails are baseline deterministic controls, not a complete security policy layer.
- Local Compose settings are designed for development, not a hardened deployment.

## Future Work

- Add Postgres repositories for sessions, approvals, audit events, and evaluation results.
- Add authentication, authorization, rate limiting, tenant isolation, and secrets management.
- Integrate a governed approval workflow and approved production embedding service.
- Add CI/CD quality gates, monitoring, model governance, and expanded regression evaluation.
