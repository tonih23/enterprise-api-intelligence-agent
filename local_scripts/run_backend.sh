#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ ! -f ".env" ]]; then
  printf 'Missing .env. Create local configuration first:\n  cp .env.example .env\n' >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source ".env"
set +a

printf 'Starting local OpenSearch, Postgres, and Phoenix services...\n'
docker compose --env-file ".env" up -d --wait opensearch postgres phoenix

printf 'Ingesting synthetic documentation...\n'
uv run python scripts/ingest_docs.py

printf 'Starting FastAPI backend at http://127.0.0.1:8000 ...\n'
exec uv run uvicorn app.main:app --reload
