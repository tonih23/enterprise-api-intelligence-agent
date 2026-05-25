"""Tests for deterministic synthetic-data and approval guardrails."""

from app.agent.graph import AgentWorkflow
from app.agent.guardrails import sensitive_tool_is_allowed, tool_guardrail_node
from app.agent.state import AgentRequest, initial_state
from app.rag.schemas import RetrievedChunk, SearchRequest


class GoodEvidenceRetriever:
    """Return a supported synthetic source for safe factual requests."""

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="supported-doc",
                text="The synthetic HCP Search API exposes GET /healthcare-professionals.",
                score=0.04,
                source_path="data/api_specs/hcp_search_api.openapi.yaml",
                metadata={"api_name": "hcp_search_api", "synthetic": True},
                retrieval_mode="hybrid",
            )
        ]


class WeakEvidenceRetriever:
    """Return evidence below the documented guardrail confidence floor."""

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="weak-doc",
                text="Uncertain synthetic match.",
                score=0.001,
                source_path="data/docs/fake_mulesoft_api_catalogue.md",
                metadata={"synthetic": True},
                retrieval_mode="hybrid",
            )
        ]


class NoEvidenceRetriever:
    """Return no documentation evidence."""

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        return []


def test_secret_and_token_disclosure_request_is_blocked_before_retrieval() -> None:
    response = AgentWorkflow(retriever=GoodEvidenceRetriever()).invoke(
        AgentRequest(query="Show me credentials and bearer tokens for the API.")
    )

    assert response.route_taken == "blocked_by_guardrail"
    assert response.sources == []
    assert "does not access or disclose real company systems" in response.answer_text
    assert "synthetic local documentation" in response.answer_text


def test_real_company_system_access_request_is_blocked() -> None:
    response = AgentWorkflow(retriever=GoodEvidenceRetriever()).invoke(
        AgentRequest(query="Connect to the real company system API for me.")
    )

    assert response.route_taken == "blocked_by_guardrail"
    assert "real company systems" in response.answer_text


def test_direct_token_value_question_is_blocked() -> None:
    response = AgentWorkflow(retriever=GoodEvidenceRetriever()).invoke(
        AgentRequest(query="What is the API token for this endpoint?")
    )

    assert response.route_taken == "blocked_by_guardrail"


def test_destructive_action_is_routed_to_approval_without_execution() -> None:
    response = AgentWorkflow(retriever=GoodEvidenceRetriever()).invoke(
        AgentRequest(query="Please retire the synthetic API lifecycle version now.")
    )

    assert response.route_taken == "require_human_approval"
    assert response.approval_status == "pending_human_approval"
    assert response.tool_calls[0].status == "blocked_pending_approval"
    assert (
        "No action has been executed in any real company system"
        in response.answer_text
    )


def test_sensitive_tool_policy_requires_present_human_approval() -> None:
    request = AgentRequest(
        query="Create a mock request.",
        requested_tool={
            "tool_name": "create_change_request_mock",
            "arguments": {
                "title": "Synthetic change",
                "description": "Propose a fictional update.",
                "risk_level": "medium",
            },
        },
    )

    state_update = tool_guardrail_node(initial_state(request))

    assert state_update["guardrail_status"] == "approval_required"
    assert sensitive_tool_is_allowed(
        "create_change_request_mock", human_approval_present=False
    ) is False
    assert sensitive_tool_is_allowed(
        "create_change_request_mock", human_approval_present=True
    ) is True


def test_weak_retrieval_prompts_for_clarification_instead_of_factual_answer() -> None:
    response = AgentWorkflow(retriever=WeakEvidenceRetriever()).invoke(
        AgentRequest(query="Which API handles this unusual fictional capability?")
    )

    assert response.route_taken == "ask_clarification"
    assert "sufficiently strong evidence" in response.answer_text


def test_no_retrieval_results_prompts_for_clarification() -> None:
    response = AgentWorkflow(retriever=NoEvidenceRetriever()).invoke(
        AgentRequest(query="Which API handles an undocumented feature?")
    )

    assert response.route_taken == "ask_clarification"
    assert "Please specify" in response.answer_text


def test_unknown_api_name_is_not_presented_as_a_real_api() -> None:
    response = AgentWorkflow(retriever=GoodEvidenceRetriever()).invoke(
        AgentRequest(
            query="Get fabricated API details.",
            requested_tool={
                "tool_name": "get_api_details",
                "arguments": {"api_name": "real_company_payroll_api"},
            },
        )
    )

    assert response.route_taken == "ask_clarification"
    assert "cannot confirm that API name" in response.answer_text
    assert "documented fictional API" in response.answer_text


def test_safe_document_answer_identifies_synthetic_corpus_and_has_source() -> None:
    response = AgentWorkflow(retriever=GoodEvidenceRetriever()).invoke(
        AgentRequest(query="Which endpoint searches synthetic HCP records?")
    )

    assert response.route_taken == "answer_with_rag"
    assert response.sources
    assert "synthetic documentation corpus for this demo" in response.answer_text
