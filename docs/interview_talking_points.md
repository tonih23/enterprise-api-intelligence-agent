# Enterprise API Intelligence Agent: Interview Talking Points

## One-Minute Summary

Enterprise API Intelligence Agent is a production-style reference project inspired by API governance and AgentOps patterns. It uses a FastAPI service and LangGraph workflow to answer questions from a fully synthetic API documentation corpus. Hybrid retrieval in OpenSearch handles both precise API identifiers and conceptual queries. MCP provides a clean tool interface, while sensitive tool actions stop at a human approval gate. Postgres stores operational metadata and Phoenix makes traces and evaluation results visible.

## Problem Statement

API users often need to locate the correct endpoint, version, parameter, or policy quickly. A conversational interface helps, but an enterprise-style solution must also answer from evidence, control tool side effects, and make quality measurable. This project demonstrates those controls using fake specifications and fake collections rather than internal data.

## Design Choices To Explain

### Why use LangGraph instead of a simple chat loop?

The workflow has meaningful states: retrieve evidence, select a tool, pause for approval, resume after a decision, and record outcomes. LangGraph makes those transitions explicit and testable. This matters when auditability and human control are requirements, not optional features.

### Why expose tools through MCP?

MCP separates tool contracts from agent prompts and model-specific code. It creates an interoperable capability layer with structured schemas and policy metadata. In this project, read-only API lookup tools can execute directly, while synthetic sensitive actions are labeled for approval.

### Why hybrid RAG?

API documentation combines exact-match language with conceptual instructions. A query for `/v1/payments/{id}` or `HTTP 409` benefits from lexical retrieval; a query about idempotent retries or credential rotation benefits from semantic similarity. Hybrid retrieval is intended to produce better grounded evidence across both query types.

### Why OpenSearch?

It supports keyword search, vector search, filters, and metadata-aware indexing in a single service. That keeps the retrieval design realistic for enterprise search while remaining reproducible through Docker Compose.

### Why human approval?

An agent that can call tools needs a clear boundary around side effects. Sensitive proposals must show what will happen and wait for a recorded reviewer decision. The approval step is enforced by the workflow and verified in tests, rather than left to prompt wording.

### Why Phoenix tracing and evaluation?

Tracing explains how an answer was produced: retrieved chunks, graph path, tool calls, latency, failures, and policy decisions. Evaluation turns that visibility into engineering feedback by measuring retrieval relevance, answer groundedness, tool-choice correctness, and approval compliance.

## AgentOps Narrative

This project treats an agent as an operated software system:

- Evidence is versioned and retrievable, with citations returned to the caller.
- Capabilities are structured as tools with clear risk classifications.
- Sensitive actions are governed through a durable approval lifecycle.
- Behavior is observable through traces rather than inferred from final text alone.
- Quality is assessed with repeatable synthetic evaluation cases.
- Configuration, local dependencies, and tests make the system reproducible.

## Example Demonstration Story

1. Ask which synthetic Payments API endpoint retrieves a transaction and what authentication it requires.
2. Show a grounded response with citations from the indexed fake OpenAPI and documentation content.
3. Ask the agent to propose registering a new synthetic API consumer.
4. Show the LangGraph workflow returning a pending approval rather than performing the action.
5. Submit an approval decision and show the completed synthetic tool event in the audit metadata.
6. Inspect a Phoenix trace and evaluation result to explain the retrieval path, tool decision, and policy outcome.

## Engineering Trade-Offs

| Choice | Benefit | Trade-off |
| --- | --- | --- |
| LangGraph state machine | Controllable, resumable workflow | More explicit state management than a basic chain |
| MCP service boundary | Reusable tool contracts and policy separation | Additional service and contract testing |
| OpenSearch hybrid retrieval | Strong exact and semantic search behavior | Index tuning and local resource requirements |
| Postgres audit metadata | Durable, queryable workflow record | Schema evolution and retention planning |
| Approval before sensitive tools | Human oversight and auditability | Added latency for action completion |
| Phoenix evaluation | Operational evidence for improvement | Requires curated cases and metric interpretation |

## Questions I Would Expect

**How do you prevent hallucinated API guidance?**

Retrieve from a controlled synthetic corpus, attach citations, constrain responses to retrieved evidence, and evaluate groundedness and source relevance.

**How do you prove an agent cannot take an unapproved action?**

Represent tool risk in structured metadata, route sensitive calls to a pending approval state, require durable approval before execution, and test attempted bypass paths.

**What would need to change for a real deployment?**

Add organization-specific authentication and authorization, secret management, retention and redaction policy, managed infrastructure, network controls, security testing, and an approved real documentation ingestion process.

**How is success measured?**

Measure retrieval relevance, citation correctness, grounded answers, correct tool routing, zero policy bypasses in tests and evaluations, latency, failure rates, and human review outcomes.

## Honest Positioning

This is an enterprise-style engineering project built with synthetic data to demonstrate architecture and controls. It is inspired by general MCP and API governance patterns. It is not an internal company system, does not contain proprietary documentation, and does not claim production authorization for real actions.
