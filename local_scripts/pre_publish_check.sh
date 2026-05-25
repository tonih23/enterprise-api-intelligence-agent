#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

fail() {
  printf 'Pre-publish check failed: %s\n' "$1" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git is required."
command -v uv >/dev/null 2>&1 || fail "uv is required. Install uv before publishing."

tracked_env_files="$(
  git ls-files -- ".env" ".env.*" \
    | awk '$0 != ".env.example" { print }'
)"
if [[ -n "${tracked_env_files}" ]]; then
  printf 'Tracked local environment file(s) detected:\n%s\n' "${tracked_env_files}" >&2
  fail "remove local environment files from Git before publishing."
fi

if ! git check-ignore --quiet --no-index ".env"; then
  fail ".env is not ignored by Git. Add it to .gitignore before publishing."
fi

printf 'Scanning tracked files for obvious API key patterns...\n'
secret_report="$(mktemp)"
trap 'rm -f "${secret_report}"' EXIT
if git grep -nE 'AIza[0-9A-Za-z_-]{20,}|lsv2_[0-9A-Za-z_-]{10,}' -- \
  >"${secret_report}"; then
  cat "${secret_report}" >&2
  fail "potential Google or LangSmith API key found in tracked files."
fi

if uv run ruff --version >/dev/null 2>&1; then
  printf 'Running Ruff formatting check...\n'
  uv run ruff format --check .
  printf 'Running Ruff lint check...\n'
  uv run ruff check .
else
  printf 'Ruff is unavailable; skipping Ruff checks.\n'
fi

printf 'Running tests in deterministic no-export mode...\n'
env API_AGENT_LLM_PROVIDER="none" API_AGENT_TRACING_BACKEND="none" uv run pytest

printf 'Running synthetic evaluations in deterministic no-export mode...\n'
env API_AGENT_LLM_PROVIDER="none" API_AGENT_TRACING_BACKEND="none" \
  uv run python -m app.evals.run_evals

printf 'Pre-publish checks passed. Review screenshots and Git status before pushing.\n'
