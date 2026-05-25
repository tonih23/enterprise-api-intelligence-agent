# Interview Talking Points

This is an enterprise-style portfolio PoC inspired by API governance,
MCP/tooling, and regulated AI patterns. It uses synthetic data only and does
not represent an internal company system.

## 1. What does the project demonstrate?

It demonstrates a controlled agent workflow for API documentation: FastAPI
exposes the service, LangGraph coordinates retrieval and tool decisions,
OpenSearch supplies hybrid RAG over fictional documentation, local MCP-style
tools expose structured capabilities, and Phoenix/evaluations make behavior
inspectable. Side-effect-like behavior is represented only by approval-gated
mock actions.

## 2. Why is hybrid RAG useful for API documentation?

API questions mix exact strings with intent. BM25 is strong for endpoint
paths, API names, versions, scopes, and error codes; vector search is useful
for questions phrased differently from a runbook or specification. Combining
both improves the chance of returning evidence for technical identifiers and
semantic questions without relying on generated knowledge.

## 3. Why use MCP-style tools?

Tools turn capabilities into explicit contracts with typed inputs, outputs,
and risk expectations. A catalogue lookup or local spec validation can be
handled predictably, while a mock change request is visibly marked for human
approval. This is easier to govern and test than hiding actions inside prompt
instructions.

## 4. Why LangGraph instead of simple function calling?

The workflow needs visible transitions: route a request, retrieve evidence,
call a tool, stop for approval, and form a sourced response. LangGraph keeps
that state and branching explicit and testable. The current router is
deterministic for repeatable tests; an LLM router could later be added behind
the same controlled workflow boundary.

## 5. How are human-in-the-loop controls and guardrails handled?

Requests for secrets, private data, or real company-system access are refused.
Factual documentation answers require synthetic sources, and weak retrieval
causes a clarification response. A change-management request is held pending
approval before the mock tool result can be returned. Tracing and synthetic
evaluations provide evidence that these paths operate as expected.

## 6. How would the local PoC evolve for production?

The local stack is useful for demonstrating design choices, not for claiming
production readiness. A deployed system would require managed infrastructure,
durable audit storage, authentication and authorization, tenant isolation,
security and model-governance reviews, and real approval integration.
Embeddings would normally come from an approved internal endpoint or a hosted
approved model rather than an unmanaged workstation download.
