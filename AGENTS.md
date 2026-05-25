# Project instructions

Build a production-style AI engineering project called Enterprise API Intelligence Agent.

Goal:
Create an enterprise-style agent that can answer questions about API documentation, retrieve relevant documentation with hybrid RAG, call MCP tools, require human approval for sensitive actions, and expose everything through FastAPI.

Tech stack:
- Python 3.11
- FastAPI
- LangGraph
- OpenSearch
- Postgres
- MCP Python SDK
- Docker Compose
- Arize Phoenix for tracing/evaluation
- pytest
- ruff
- mypy optional

Rules:
- Do not use internal company data.
- Use synthetic API docs, fake OpenAPI specs and fake Postman collections.
- Keep architecture clean and modular.
- Prefer simple working code over over-engineered abstractions.
- Every task must include tests where reasonable.
- Add README documentation for every major module.
- Never hardcode API keys.
- Use environment variables.
- Add .env.example.
- After each implementation, run tests and fix errors.
- Do not claim this is an AstraZeneca internal project.
- Phrase it as an enterprise-style project inspired by MCP/API governance patterns.