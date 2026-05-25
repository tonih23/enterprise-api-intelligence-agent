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
| `opensearch` | [http://127.0.0.1:9200](http://127.0.0.1:9200) | Future hybrid retrieval index |
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

- `sentence_transformers` creates real semantic embeddings with the configured
  model. It is the production-style backend and downloads model artifacts on
  first use unless they are already cached.
- `local_hashing` creates deterministic, normalized lexical feature-hash
  vectors with no network access or model download. It is only a local
  development and CI fallback, not a production semantic embedding approach.

Switch backends in `.env`:

```dotenv
# No-network local or CI ingestion
API_AGENT_EMBEDDING_BACKEND="local_hashing"

# Semantic embedding ingestion
API_AGENT_EMBEDDING_BACKEND="sentence_transformers"
API_AGENT_EMBEDDING_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2"
```

The local hashing dimension is `384`, matching the default semantic model
dimension for convenient local testing. Running ingestion again replaces
chunks with matching stable identifiers rather than intentionally duplicating
them.

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
| `API_AGENT_EMBEDDING_MODEL_NAME` | Model used by the `sentence_transformers` backend | `sentence-transformers/all-MiniLM-L6-v2` |
| `API_AGENT_EMBEDDING_BATCH_SIZE` | Number of chunk texts embedded per batch | `32` |
| `API_AGENT_RAG_CHUNK_SIZE` | Maximum chunk size in characters | `1000` |
| `API_AGENT_RAG_CHUNK_OVERLAP` | Repeated context between adjacent chunks | `150` |
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

Future phases introduce LangGraph workflow orchestration, an MCP tool server,
hybrid ranking and answer generation over the indexed fictional documentation,
Postgres operational metadata integration, and Phoenix tracing and evaluation
instrumentation. All corpus content and examples will remain synthetic.
