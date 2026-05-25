# Public GitHub Publish Guide

This repository is an enterprise-style AI Engineering portfolio PoC over
synthetic data only. It is not a deployed production service and does not use
real company systems.

## Prerequisites

- Python 3.11.
- [uv](https://docs.astral.sh/uv/).
- Docker Compose.
- Git and, optionally, the [GitHub CLI](https://cli.github.com/).

## Configure Locally

Create the ignored local environment file:

```bash
cp .env.example .env
```

For the default offline-friendly demo, keep:

```dotenv
API_AGENT_EMBEDDING_BACKEND="local_hashing"
API_AGENT_LLM_PROVIDER="none"
API_AGENT_TRACING_BACKEND="none"
```

Replace the sample `POSTGRES_PASSWORD` value in `.env` before starting
Compose. No external API key is required for the default local workflow.

| Variable | Required For | Notes |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | Local Compose services | Replace the placeholder locally; Phoenix uses the same local database. |
| `API_AGENT_EMBEDDING_BACKEND` | Retrieval ingestion | `local_hashing` default requires no model download. |
| `API_AGENT_LLM_PROVIDER` | Answer wording | `none` default requires no external key. |
| `API_AGENT_TRACING_BACKEND` | Trace export | `none` default exports nothing. |
| `GOOGLE_API_KEY` | Optional Gemini demo only | Keep only in `.env`; never commit it. |
| `LANGSMITH_API_KEY` | Optional LangSmith tracing only | Keep only in `.env`; never commit it. |

Optional local demo features are configured only in `.env`:

- Set `API_AGENT_TRACING_BACKEND="phoenix"` for local Phoenix tracing.
- Set `API_AGENT_LLM_PROVIDER="gemini"` and populate the commented
  `GOOGLE_API_KEY` variable locally for optional answer synthesis.
- Set `API_AGENT_TRACING_BACKEND="langsmith"` and populate the commented
  `LANGSMITH_API_KEY` variable locally for optional managed tracing.

Never commit `.env`, screenshots containing credentials, or populated key
values.

## Run The Demo

Install dependencies once:

```bash
uv sync --dev
```

Start infrastructure, ingest synthetic documents, and run FastAPI:

```bash
./local_scripts/run_backend.sh
```

In another terminal, start the Streamlit UI:

```bash
./local_scripts/run_ui.sh
```

Useful local URLs:

| Surface | URL |
| --- | --- |
| Streamlit UI | `http://127.0.0.1:8501` |
| FastAPI docs | `http://127.0.0.1:8000/docs` |
| Phoenix | `http://127.0.0.1:6006` |

## Test And Evaluate

```bash
./local_scripts/run_evals.sh
./local_scripts/pre_publish_check.sh
```

`pre_publish_check.sh` runs formatting/lint checks when available, pytest,
offline synthetic evaluations, an ignored-`.env` check, and a tracked-file
scan for obvious Google or LangSmith key patterns. It forces deterministic
answer and no-export tracing modes for its test/evaluation execution.

## Observability Options

### Phoenix

Phoenix is the local/open-source demonstration path. In `.env`, set:

```dotenv
API_AGENT_TRACING_BACKEND="phoenix"
```

`run_backend.sh` starts the Phoenix service alongside its local Postgres
dependency. Open `http://127.0.0.1:6006` and inspect `agent.run` traces and
their workflow child spans.

### LangSmith

LangSmith is an optional managed tracing path that is natural to discuss with
a LangGraph workflow. Configure it locally by selecting `langsmith` and
setting a personal API key only in the ignored `.env` file. The free tier is
suitable for a small portfolio demonstration.

LangSmith access may fail on corporate networks because of SSL inspection,
proxy rules, or outbound network restrictions. The application falls back to
no-op tracing if it cannot initialize tracing; local agent behavior still
works.

## Publish With GitHub CLI

After reviewing the files and capturing only public-safe screenshots:

```bash
git status --short
git add .
./local_scripts/pre_publish_check.sh
git commit -m "Prepare public portfolio release"
gh auth login
gh repo create enterprise-api-intelligence-agent --public --source=. --remote=origin --push
```

Confirm in GitHub that `.env` and any local model folders are absent from the
published files.

## Publish With Git

Create an empty public repository in GitHub, then connect and push:

```bash
git status --short
git add .
./local_scripts/pre_publish_check.sh
git commit -m "Prepare public portfolio release"
git remote add origin https://github.com/YOUR_USERNAME/enterprise-api-intelligence-agent.git
git branch -M main
git push -u origin main
```

Before sharing the URL, review the rendered README, screenshots, repository
file list, and GitHub secret-scanning alerts.
