# Evaluation Module

This module provides a deterministic baseline evaluation suite over fictional
API documentation and mock governed actions only.

- `test_set.yaml` contains 20 synthetic questions with expected routes,
  evidence documents, and local tool selections where applicable.
- `metrics.py` defines typed observations and aggregate metric functions.
- `run_evals.py` executes the existing LangGraph workflow with a local
  token-overlap corpus retriever so the baseline requires no OpenSearch,
  database, embedding download, or LLM API.

Run the suite from the repository root:

```bash
uv run python -m app.evals.run_evals
```

The command writes a local ignored artifact to
`artifacts/evals/latest.json`. If `ENABLE_TRACING=true`, normal agent spans
are optionally sent to the configured local Phoenix collector.
