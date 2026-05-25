"""Tests for deterministic LangGraph routing and approval controls."""

from app.agent.graph import AgentWorkflow, create_agent_workflow
from app.agent.state import AgentRequest
from app.config import Settings
from app.mcp_server.schemas import ApiDetails, MockChangeRequest, ToolPolicy
from app.rag.schemas import RetrievedChunk, SearchRequest


class FakeRetriever:
    """Return stable synthetic evidence without OpenSearch or embeddings."""

    def __init__(self) -> None:
        self.requests: list[SearchRequest] = []

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        self.requests.append(request)
        return [
            RetrievedChunk(
                chunk_id="approval-doc",
                text="POST /trial-interest-requests needs human approval.",
                score=0.04,
                source_path="data/docs/api_governance_runbook.md",
                metadata={"api_name": "clinical_trials_api"},
                retrieval_mode="hybrid",
            )
        ]


class FakeMcpTools:
    """Record tool invocations while returning synthetic local results."""

    def __init__(self) -> None:
        self.details_calls: list[str] = []
        self.change_request_calls: list[tuple[str, str, str]] = []

    def get_api_details(self, api_name: str) -> ApiDetails:
        self.details_calls.append(api_name)
        return ApiDetails(
            api_name=api_name,
            title="Fictional Clinical Trials API",
            version="2.1.0",
            source_path="data/api_specs/clinical_trials_api.openapi.yaml",
            metadata={"api_name": api_name, "synthetic": True},
            server_urls=[],
            operations=[],
        )

    def create_change_request_mock(
        self, title: str, description: str, risk_level: str
    ) -> MockChangeRequest:
        self.change_request_calls.append((title, description, risk_level))
        return MockChangeRequest(
            change_request_id="CR-MOCK-SHOULD-NOT-RUN",
            title=title,
            description=description,
            risk_level=risk_level,  # type: ignore[arg-type]
            policy=ToolPolicy(
                risk_level="high",
                requires_human_approval=True,
                side_effects=False,
            ),
        )


def test_document_question_routes_to_hybrid_rag_and_returns_sources() -> None:
    retriever = FakeRetriever()
    workflow = AgentWorkflow(retriever=retriever, mcp_tools=FakeMcpTools())

    response = workflow.invoke(
        AgentRequest(query="Which clinical trial operation needs approval?")
    )

    assert response.route_taken == "answer_with_rag"
    assert retriever.requests[0].mode == "hybrid"
    assert response.sources[0].chunk_id == "approval-doc"
    assert "synthetic documentation corpus" in response.answer_text
    assert response.tool_calls == []


def test_explicit_local_lookup_routes_to_mcp_tool() -> None:
    tools = FakeMcpTools()
    workflow = AgentWorkflow(retriever=FakeRetriever(), mcp_tools=tools)

    response = workflow.invoke(
        AgentRequest(
            query="Show the clinical trials API details.",
            requested_tool={
                "tool_name": "get_api_details",
                "arguments": {"api_name": "clinical_trials_api"},
            },
        )
    )

    assert response.route_taken == "call_mcp_tool"
    assert tools.details_calls == ["clinical_trials_api"]
    assert response.tool_calls[0].tool_name == "get_api_details"
    assert response.tool_calls[0].status == "completed"
    assert response.sources[0].source_path.endswith("clinical_trials_api.openapi.yaml")


def test_ambiguous_request_routes_to_clarification_without_retrieval() -> None:
    retriever = FakeRetriever()
    workflow = AgentWorkflow(retriever=retriever, mcp_tools=FakeMcpTools())

    response = workflow.invoke(AgentRequest(query="help"))

    assert response.route_taken == "ask_clarification"
    assert "Please specify" in response.answer_text
    assert retriever.requests == []


def test_mock_change_request_is_blocked_pending_approval_without_tool_call() -> None:
    tools = FakeMcpTools()
    workflow = AgentWorkflow(retriever=FakeRetriever(), mcp_tools=tools)

    response = workflow.invoke(
        AgentRequest(
            query="Create a fictional change request for the trial schema.",
            requested_tool={
                "tool_name": "create_change_request_mock",
                "arguments": {
                    "title": "Update trial schema",
                    "description": "Add a synthetic status filter.",
                    "risk_level": "medium",
                },
            },
        )
    )

    assert response.route_taken == "require_human_approval"
    assert response.approval_status == "pending_human_approval"
    assert response.tool_calls[0].status == "blocked_pending_approval"
    assert response.tool_calls[0].requires_human_approval is True
    assert tools.change_request_calls == []
    assert "No action has been executed" in response.answer_text


def test_unstructured_change_request_intent_is_also_approval_gated() -> None:
    workflow = AgentWorkflow(retriever=FakeRetriever(), mcp_tools=FakeMcpTools())

    response = workflow.invoke(
        AgentRequest(query="Please create change request for an API update.")
    )

    assert response.route_taken == "require_human_approval"
    assert response.tool_calls[0].tool_name == "create_change_request_mock"


def test_workflow_factory_uses_configured_router_backend() -> None:
    workflow = create_agent_workflow(
        retriever=FakeRetriever(),
        mcp_tools=FakeMcpTools(),
        settings=Settings(environment="test", router_backend="deterministic"),
    )

    response = workflow.invoke(AgentRequest(query="Which API exposes trial search?"))

    assert response.route_taken == "answer_with_rag"


def test_mcp_branch_reads_real_local_synthetic_spec_without_network() -> None:
    workflow = AgentWorkflow(retriever=FakeRetriever())

    response = workflow.invoke(
        AgentRequest(
            query="Read the synthetic HCP API metadata.",
            requested_tool={
                "tool_name": "get_api_details",
                "arguments": {"api_name": "hcp_search_api"},
            },
        )
    )

    assert response.route_taken == "call_mcp_tool"
    assert response.tool_calls[0].status == "completed"
    assert (
        response.sources[0].source_path == "data/api_specs/hcp_search_api.openapi.yaml"
    )
