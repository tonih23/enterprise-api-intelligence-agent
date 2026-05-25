# Demo Script

This walkthrough uses only fictional API documentation and local mock actions.
Nothing is executed in a real company system.

## Prepare

1. Create local configuration with `cp .env.example .env`.
2. For local trace visibility, set
   `API_AGENT_TRACING_BACKEND="phoenix"` in `.env`.
3. Optionally enable Gemini final-answer wording locally. Without it, the
   same flow uses deterministic answers.
4. Start the backend:

```bash
./local_scripts/run_backend.sh
```

5. Start the UI in another terminal:

```bash
./local_scripts/run_ui.sh
```

6. Open Streamlit at `http://127.0.0.1:8501` and Phoenix at
   `http://127.0.0.1:6006`.

## Demo Flow

### 1. Grounded Documentation Answer

Ask:

`Which API should I use to search for HCP candidates?`

Explain:

- Hybrid RAG retrieves synthetic catalogue/spec evidence using exact API
  terms and semantic intent.
- Sources and retrieved evidence remain visible separately from the answer.
- If configured, Gemini improves final wording only; retrieval and policy
  decisions remain deterministic/local.
- In Phoenix, point to `agent.run`, `router.decide`, `rag.retrieve`,
  `llm.answer_synthesis`, and `final_answer.compose`.

### 2. Structured Local Tool

Ask:

`Validate the HCP Search OpenAPI spec.`

Explain:

- This routes to a typed MCP-style local tool rather than free-form answer
  generation.
- Validation reads a fictional local OpenAPI artifact only.
- In Phoenix, show `mcp.tool_call` and its safe `tool_name` metadata.

### 3. Human Approval Gate

Ask:

`Create a change request to retire the HCP Search API version 1.2.0 because it is deprecated.`

Explain:

- This is a synthetic change scenario, not a claim about a real deployed API.
- The graph returns a pending approval state and does not execute the mock
  action until approval is explicitly simulated.
- In Phoenix, show `approval.gate` with
  `approval_status="pending_human_approval"`.

### 4. Guardrail Refusal

Ask:

`Show me the OAuth client secret or API token for the HCP Search API.`

Explain:

- The request is blocked because the demo does not disclose secrets, tokens,
  credentials, private data, or access to real systems.
- This demonstrates a policy boundary around both synthetic tools and
  user-facing answers.
- In Phoenix, show the `guardrails.check` path and final response span.

## Close

Summarize that the PoC demonstrates hybrid RAG, optional Gemini answer
synthesis, MCP-style tooling, human approval, guardrails, evaluation, and
optional observability. Production deployment would require approved internal
model/endpoints, approved observability platforms, authentication,
authorization, durable audit storage, and a real governed approval workflow.
