# Screenshot Checklist

Capture only the synthetic demo and safe workflow metadata. Before publishing,
check that screenshots do not show `.env` contents, API keys, browser
credentials, terminal history containing keys, or private account details.

Store selected images under `assets/screenshots/`.

| Capture | Recommended File Name | Notes |
| --- | --- | --- |
| Streamlit home screen | `01-streamlit-home.png` | Show the clean question form and local-demo framing. |
| RAG answer with Gemini synthesis and sources | `02-rag-gemini-sources.png` | Capture only after optional Gemini is configured locally; show source/evidence panels, never the key. |
| MCP OpenAPI validation result | `03-mcp-openapi-validation.png` | Show local fictional spec validation and tool call section. |
| Human approval pending result | `04-human-approval-pending.png` | Show pending approval before clicking any simulated approval button. |
| Guardrail blocking secret/token request | `05-guardrail-secret-blocked.png` | Show refusal without entering or exposing an actual token. |
| Phoenix trace with workflow spans | `06-phoenix-agent-trace.png` | Show `agent.run` plus safe child span names/metadata only. |
| FastAPI docs page | `07-fastapi-docs.png` | Show `/docs` endpoints without local secret configuration. |
| Optional LangSmith trace page | `08-langsmith-trace-optional.png` | Include only if working; hide account/private project details as needed. |

## Before Commit

- Verify each image reflects synthetic/demo data only.
- Crop or redact local usernames, API keys, credentials, and irrelevant tabs.
- Confirm any LangSmith capture contains trace metadata only, not sensitive
  account details.
- Run `./local_scripts/pre_publish_check.sh` before publishing.
