# LLM Module

This module optionally improves final answer wording without changing retrieval,
tool execution, guardrails, or human approval.

- `API_AGENT_LLM_PROVIDER="none"` is the default and keeps deterministic
  answers with no API key.
- `API_AGENT_LLM_PROVIDER="gemini"` uses the official Google GenAI SDK only
  during final answer synthesis.
- `GOOGLE_API_KEY` is read from the environment or local `.env` only when
  Gemini is selected.

If Gemini cannot be configured or called, the agent returns its deterministic
answer with an `answer_synthesis.warning` value rather than failing the run.
