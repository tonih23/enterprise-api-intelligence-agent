# Screenshot Checklist

Capture only the synthetic demo and safe workflow metadata. Before publishing,
check that screenshots do not show `.env` contents, API keys, browser
credentials, terminal history containing keys, or private account details.

Store selected images under `assets/screenshots/`.

| Capture | Recommended File Name | Notes |
| --- | --- | --- |
| Streamlit demo UI | `01-streamlit-home.png` | Show the clean question form and local-demo framing. |
| RAG answer with Gemini synthesis status | `02-rag-gemini-answer.png` | Show the answer and displayed synthesis status; never imply Gemini ran if deterministic fallback is shown. |
| Retrieved evidence / sources | `02-rag-gemini-sources.png` | Show the source and evidence panels for the grounded answer. |
| MCP OpenAPI validation | `03-mcp-openapi-validation.png` | Show local fictional spec validation and tool call section. |
| MCP validation details | `03-mcp-openapi-validation-details.png` | Show expanded synthetic validation metadata. |
| Human approval pending | `04-human-approval-pending.png` | Show pending approval before clicking any simulated approval button. |
| Human approval approved result | `04-human-approved.png` | Show the returned mock result and that no external record was created. |
| Guardrail blocking secret/token request | `05-guardrail-secret-blocked.png` | Show refusal without entering or exposing an actual token. |
| Phoenix trace with workflow spans | `06-phoenix-agent-trace.png` | Show `agent.run` plus safe child span names/metadata only. |
| FastAPI docs page | `07-fastapi-docs.png` | Show `/docs` endpoints without local secret configuration. |

## Before Commit

- Verify each image reflects synthetic/demo data only.
- Crop or redact local usernames, API keys, credentials, and irrelevant tabs.
- Run `./local_scripts/pre_publish_check.sh` before publishing.
