# MCP Tools

## Purpose

The local MCP server exposes controlled capabilities for the Enterprise API
Intelligence Agent. All tools operate on fictional local project data or
return synthetic mock objects. They do not connect to company systems,
production APIs, ticketing platforms, or identity providers.

Run the stdio server locally:

```bash
uv run python -m app.mcp_server.server
```

## Tool Catalogue

| Tool | Risk Level | Human Approval Required | Side Effects | Intended Use |
| --- | --- | --- | --- | --- |
| `search_api_catalog` | Low | No | No | Find relevant synthetic API documentation passages |
| `get_api_details` | Low | No | No | Inspect metadata and operations for a known fictional API |
| `validate_openapi_spec` | Low | No | No | Check local synthetic API specifications before ingestion or discussion |
| `create_change_request_mock` | Medium minimum, or high when requested | Yes | No external side effect | Demonstrate an approval-gated change proposal workflow |

## `search_api_catalog(query, filters)`

Uses the existing hybrid RAG retriever, combining BM25 and configured-vector
rankings. The selected OpenSearch index must already be ingested with a vector
dimension compatible with the configured embedding backend.

Inputs:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | Yes | Question or technical search phrase |
| `filters` | object or null | No | Exact filters for `domain`, `system`, `api_name`, and `data_classification` |

Output:

- Query and retrieval mode (`hybrid`).
- Ranked evidence chunks including `chunk_id`, `text`, `score`,
  `source_path`, metadata, and retrieval mode.
- Read-only tool policy metadata.

The agent should use this tool when answering questions that require cited
documentation evidence, including endpoint discovery, access scopes, and
governance guidance.

## `get_api_details(api_name)`

Reads a local synthetic OpenAPI specification matching the requested
`api_name` and summarizes its metadata and operations.

Inputs:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `api_name` | string | Yes | Metadata identifier such as `hcp_search_api` or `clinical_trials_api` |

Output:

- API title, version, description, metadata, local source path, and sandbox
  server URLs.
- Operation summaries, including whether each operation requires human
  approval.
- Read-only tool policy metadata.

The agent should use this tool when the caller already knows an API name and
needs structured details rather than broad retrieval.

## `validate_openapi_spec(spec_path)`

Performs basic structure validation on JSON or YAML files located under the
project's local `data/api_specs` directory. It checks the OpenAPI version,
required `info` fields, synthetic metadata, and presence of paths.

Inputs:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `spec_path` | string | Yes | Filename such as `hcp_search_api.openapi.yaml` or project-relative path under `data/api_specs` |

Output:

- Validation status, errors, local source path, API name, version, metadata,
  and read-only tool policy.

The agent should use this tool before describing a contract as structurally
usable or when diagnosing an intentionally malformed synthetic specification.
Paths outside the synthetic specification directory are rejected.

## `create_change_request_mock(title, description, risk_level)`

Creates an in-memory response representing a fictional pending API governance
change request. It never creates a ticket, writes to an external service, or
changes an API.

Inputs:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | string | Yes | Short synthetic change title |
| `description` | string | Yes | Proposed fictional change and justification |
| `risk_level` | `low`, `medium`, or `high` | Yes | Requested change risk classification |

Output:

- Stable mock request identifier derived from the input.
- `status: pending_human_approval`.
- `synthetic: true`, `mock: true`, and `external_system_created: false`.
- `requires_human_approval: true` plus approval-required policy metadata.

**Approval control:** This tool is marked as requiring human approval even
though its current implementation only returns a mock object. An agent may
draft or display the proposal, but it must not describe the proposed change
as approved or executed. This preserves the control boundary needed if a
future implementation integrates an approved change-management service.
