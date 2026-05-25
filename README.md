# Enterprise API Intelligence Agent

Enterprise API Intelligence Agent is an enterprise-style AI engineering
reference project inspired by MCP and API governance patterns. It will answer
questions about synthetic API documentation, expose controlled tools, and make
sensitive actions subject to human approval.

This initial implementation provides a typed FastAPI service foundation and a
health endpoint. It does not use internal company data or call real APIs.

## Current Capabilities

- FastAPI application factory and executable ASGI app.
- Environment-based settings using the `API_AGENT_` prefix.
- `GET /health` endpoint with a typed response contract.
- Pytest and Ruff configuration managed through `pyproject.toml`.

The proposed end-to-end architecture and delivery sequence are documented in
[docs/architecture.md](docs/architecture.md) and
[docs/project_plan.md](docs/project_plan.md).

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.11, which `uv` can install and select from `.python-version`

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

Credentials and infrastructure connection values will be introduced only with
their corresponding modules and must always be provided through environment
configuration.

## Development Checks

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

## Planned Modules

Future phases introduce LangGraph workflow orchestration, an MCP tool server,
OpenSearch hybrid retrieval over fictional API documentation, Postgres
operational metadata, Phoenix tracing and evaluation, and Docker Compose local
services. All corpus content and examples will remain synthetic.
