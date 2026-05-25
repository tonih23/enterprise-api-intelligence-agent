# MCP Server Module

The `app.mcp_server` package exposes local MCP tools backed exclusively by the
synthetic project corpus.

- `schemas.py` defines structured, policy-aware tool results.
- `tools.py` implements framework-independent local behavior.
- `server.py` registers those capabilities with the official MCP Python SDK
  using a small `FastMCP` stdio server.

Start the server from the project root:

```bash
uv run python -m app.mcp_server.server
```

`search_api_catalog` requires an ingested OpenSearch index. Metadata and
OpenAPI validation tools read only local files in `data/api_specs`.
`create_change_request_mock` returns a fictional pending object and does not
call any external change-management system.
