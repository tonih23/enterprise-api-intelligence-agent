# Evaluation Suite

## Purpose

The evaluation suite is a small deterministic regression baseline for the
Enterprise API Intelligence Agent. It verifies that agent control flow,
synthetic evidence selection, local tool selection, and approval enforcement
remain stable as the implementation changes.

All questions refer to fictional Atlas sandbox APIs, runbooks, and mock
actions. The suite does not use company data, call an external LLM, or invoke
a real operational system.

## Dataset

`app/evals/test_set.yaml` contains 20 curated cases across four behaviors:

| Expected route | What it checks |
| --- | --- |
| `rag` | A documentation question retrieves a relevant fictional source |
| `mcp_tool` | A structured local MCP request selects the intended tool |
| `human_approval` | A sensitive mock request is stopped before execution |
| `clarification` | An ambiguous message asks for usable detail |

Cases identify an expected source document where evidence can be checked and
an expected tool name where a tool selection is part of the behavior.

## Running Locally

Run from the repository root:

```bash
uv run python -m app.evals.run_evals
```

The runner writes:

```text
artifacts/evals/latest.json
```

That artifact is intentionally ignored by Git. It contains aggregate metrics
and per-case observations for local review.

The baseline runner uses a deterministic token-overlap retriever over local
synthetic files. This keeps the suite repeatable without OpenSearch,
embedding-model downloads, or external services. It exercises the real
LangGraph routing, MCP tool service, approval gate, and final-answer logic.
Separate integration evaluations should be used to measure an indexed
OpenSearch deployment and semantic embedding configuration.

## Metrics

| Metric | Definition | Governance relevance |
| --- | --- | --- |
| `route_accuracy` | Fraction of questions sent to the expected graph route | Finds incorrect delegation or policy routing changes |
| `source_recall` | Fraction of expected source documents present in returned sources | Checks that answers retain relevant evidence |
| `tool_call_accuracy` | Fraction of tool-expected cases selecting the expected local tool | Detects incorrect capability selection |
| `approval_precision` | Fraction of approval-gated outputs that truly require approval | Detects unnecessary escalation and false policy triggers |
| `answer_groundedness` | Deterministic rubric using expected source presence, required answer terms, and approval/clarification wording | Provides a lightweight grounded-response regression signal |

`answer_groundedness` is intentionally a heuristic rubric, not an LLM judge
or a substitute for human review. A perfect score on this fixed dataset means
that known baseline expectations passed; it does not demonstrate broad
production quality.

## Results And Future Persistence

This initial implementation stores results as local JSON to avoid requiring
database migrations or a running Postgres instance for tests and developer
checks. A durable Postgres-backed evaluation repository would store:

- evaluation run identifier, dataset version, timestamp, and configuration;
- aggregate metric values;
- per-case route, expected and returned sources, selected tool, and approval
  outcome;
- a trace identifier when optional trace export is enabled.

That storage boundary supports trend analysis, release comparison, and audit
reporting while keeping the checked-in test data synthetic.

## Optional Tracing

When `API_AGENT_TRACING_BACKEND` selects Phoenix or LangSmith, each evaluated
case uses the existing optional instrumentation and can appear as an
`agent.run` trace with router, retrieval, MCP, approval, and final-answer
child spans as applicable. Legacy `ENABLE_TRACING=true` continues to select
Phoenix when no backend is specified.

The traced metadata follows the project data-minimization rule: spans record
workflow outcomes and counts, rather than question text, retrieved content, or
tool argument payloads.
