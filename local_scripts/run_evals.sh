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

printf 'Running automated tests...\n'
uv run pytest

printf 'Running synthetic evaluation suite...\n'
uv run python -m app.evals.run_evals
