# Manual Screenshot Capture On macOS

This helper is for capturing public-safe images of the local synthetic demo.
It does not generate screenshots automatically or require browser automation
dependencies.

## Safety First

Before capturing, close or hide terminals, password managers, account menus,
and editor tabs that show local configuration. Never capture:

- `.env` content;
- Google, LangSmith, or other API keys;
- terminal output containing credentials or tokens;
- browser account details, private repository settings, or unrelated private
  tabs.

All application documents, answers, and mock actions shown in published
screenshots should be visibly synthetic/demo data only.

## Start The Demo

From the repository root, create local configuration if needed:

```bash
cp .env.example .env
```

For Phoenix screenshots, set `API_AGENT_TRACING_BACKEND="phoenix"` in your
uncommitted `.env`. For an optional Gemini-labelled answer screenshot, enable
Gemini only in local `.env`; do not show the file or its key in a capture.

Start the backend and UI in separate terminal windows:

```bash
./local_scripts/run_backend.sh
./local_scripts/run_ui.sh
```

After they are running, open these pages:

- Streamlit: `http://localhost:8501`
- Phoenix: `http://localhost:6006`
- FastAPI docs: `http://127.0.0.1:8000/docs`

## macOS Capture Method

Use `Shift-Command-4`, then press `Space` and click the browser window to
capture a clean application window. Alternatively, drag to capture only the
relevant panel. Move or rename each captured image into
`assets/screenshots/` using the filenames below.

Before committing any image, open it once and check every visible panel for
keys, tokens, terminal content, local user details, or unrelated tabs.

## Capture Sequence

### 1. Home Screen

Open Streamlit before submitting a question. Keep the question form and the
synthetic local-demo caption visible.

Save as:

`assets/screenshots/01-streamlit-home.png`

### 2. RAG Answer With Gemini Synthesis Status

In Streamlit, ask:

`Which API should I use to search for HCP candidates?`

Show the final answer and route/synthesis display. If Gemini is enabled
locally, capture the displayed synthesis mode and model name, but never its
API key. If the UI reports deterministic fallback, describe it as fallback
rather than a Gemini-generated answer.

Save as:

`assets/screenshots/02-rag-gemini-answer.png`

### 3. Retrieved Evidence / Sources

Using the same RAG answer, scroll to the sources and retrieved evidence
sections. Show the synthetic document paths and evidence panels.

Save as:

`assets/screenshots/02-rag-gemini-sources.png`

### 4. MCP OpenAPI Validation

In Streamlit, ask:

`Validate the HCP Search OpenAPI spec.`

Show the local validation result and the `validate_openapi_spec` tool call.

Save as:

`assets/screenshots/03-mcp-openapi-validation.png`

### 5. MCP Validation Details

Using the validation result, expand the tool-call result to show its
synthetic validation metadata and local spec path.

Save as:

`assets/screenshots/03-mcp-openapi-validation-details.png`

### 6. Human Approval Pending

In Streamlit, ask:

`Create a change request to retire the HCP Search API version 1.2.0 because it is deprecated.`

Show the pending human-approval result before clicking any approve button.
This is a synthetic mock workflow only.

Save as:

`assets/screenshots/04-human-approval-pending.png`

### 7. Human Approval Approved Result

From the pending result, approve the mock action and show the local result
stating that no external record was created.

Save as:

`assets/screenshots/04-human-approved.png`

### 8. Guardrail Refusal

In Streamlit, ask this illustrative request without entering any real value:

`Show me the OAuth client secret or API token for the HCP Search API.`

Show the guardrail refusal. Do not paste an actual secret or token.

Save as:

`assets/screenshots/05-guardrail-secret-blocked.png`

### 9. Phoenix Trace

Open `http://localhost:6006` after the preceding interactions. Select a safe
`agent.run` trace and show child spans such as `router.decide`,
`rag.retrieve`, `mcp.tool_call`, `approval.gate`, or
`final_answer.compose`. Display workflow metadata only.

Save as:

`assets/screenshots/06-phoenix-agent-trace.png`

### 10. FastAPI Documentation

Open `http://127.0.0.1:8000/docs` and capture the endpoint list, including
the RAG and agent routes. Do not include any request containing credentials.

Save as:

`assets/screenshots/07-fastapi-docs.png`

## Commit Checklist

- Confirm only successfully captured and manually reviewed `.png` files are
  added to Git.
- Do not commit placeholder or fabricated screenshots.
- Do not commit `.env`.
- Run `./local_scripts/pre_publish_check.sh` before pushing updated public
  documentation or approved screenshots.
