"""HTTP behavior tests for local LangGraph agent endpoints."""

from collections.abc import Mapping
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.agent.api import (
    get_agent_repository,
    get_agent_workflow,
    get_approval_tools,
    get_observability_tracer,
)
from app.agent.graph import AgentWorkflow
from app.agent.repository import InMemoryAgentRepository
from app.config import Settings
from app.main import create_app
from app.mcp_server.schemas import MockChangeRequest, RiskLevel
from app.mcp_server.tools import McpToolService
from app.observability.phoenix import TraceValue
from app.rag.schemas import RetrievedChunk, SearchRequest


class FakeRetriever:
    """Return local evidence without constructing OpenSearch dependencies."""

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="chat-source",
                text=f"Synthetic guidance for: {request.query}",
                score=0.04,
                source_path="data/docs/api_governance_runbook.md",
                metadata={"synthetic": True},
                retrieval_mode="hybrid",
            )
        ]


class RecordingTools(McpToolService):
    """Run real local mock logic while recording approval-time invocation."""

    def __init__(self) -> None:
        super().__init__(retriever=FakeRetriever())
        self.change_request_calls: list[tuple[str, str, RiskLevel]] = []

    def create_change_request_mock(
        self, title: str, description: str, risk_level: RiskLevel
    ) -> MockChangeRequest:
        self.change_request_calls.append((title, description, risk_level))
        return super().create_change_request_mock(title, description, risk_level)


class RecordingSpan:
    """Minimal API-level span recorder used for approval verification."""

    def __init__(self, name: str, attributes: Mapping[str, TraceValue] | None) -> None:
        self.name = name
        self.attributes = dict(attributes or {})

    def set_attribute(self, key: str, value: TraceValue) -> None:
        self.attributes[key] = value


class RecordingTracer:
    """Collect explicit approval continuation spans without an exporter."""

    def __init__(self) -> None:
        self.spans: list[RecordingSpan] = []

    @contextmanager
    def span(self, name: str, attributes: Mapping[str, TraceValue] | None = None):
        span = RecordingSpan(name, attributes)
        self.spans.append(span)
        yield span


def build_test_client() -> tuple[TestClient, RecordingTools]:
    repository = InMemoryAgentRepository()
    tools = RecordingTools()
    workflow = AgentWorkflow(retriever=FakeRetriever(), mcp_tools=tools)
    app = create_app(Settings(environment="test", embedding_backend="local_hashing"))
    app.dependency_overrides[get_agent_repository] = lambda: repository
    app.dependency_overrides[get_agent_workflow] = lambda: workflow
    app.dependency_overrides[get_approval_tools] = lambda: tools
    return TestClient(app), tools


def test_chat_returns_graph_result_and_session_history() -> None:
    client, _ = build_test_client()

    chat = client.post(
        "/agent/chat",
        json={"user_message": "Which API guidance describes trial approval?"},
    )

    assert chat.status_code == 200
    payload = chat.json()
    assert payload["route_taken"] == "answer_with_rag"
    assert payload["sources"][0]["chunk_id"] == "chat-source"
    assert payload["approval_status"] == "not_required"
    assert payload["session_id"].startswith("session_")

    history = client.get(f"/agent/sessions/{payload['session_id']}")
    assert history.status_code == 200
    assert history.json()["messages"][0]["user_message"].startswith("Which API")
    assert history.json()["approvals"] == []


def test_chat_maps_explicit_local_api_details_command_to_mcp() -> None:
    client, _ = build_test_client()

    response = client.post(
        "/agent/chat",
        json={
            "user_message": "Get API details for hcp_search_api",
            "session_id": "interview-demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "interview-demo"
    assert payload["route_taken"] == "call_mcp_tool"
    assert payload["tool_calls"][0]["tool_name"] == "get_api_details"
    assert payload["sources"][0]["source_path"].endswith("hcp_search_api.openapi.yaml")


def test_risky_chat_returns_approval_then_executes_mock_only_after_approval() -> None:
    client, tools = build_test_client()

    chat = client.post(
        "/agent/chat",
        json={
            "user_message": "Please create a change request for a synthetic API update."
        },
    )

    assert chat.status_code == 200
    pending = chat.json()
    assert pending["route_taken"] == "require_human_approval"
    assert pending["approval_status"] == "pending_human_approval"
    assert pending["approval_id"].startswith("approval_")
    assert pending["tool_calls"][0]["status"] == "blocked_pending_approval"
    assert tools.change_request_calls == []

    approved = client.post(f"/agent/approve/{pending['approval_id']}")

    assert approved.status_code == 200
    approval_payload = approved.json()
    assert approval_payload["approval_status"] == "approved"
    assert approval_payload["approved_mock_action"]["status"] == "approved"
    assert approval_payload["approved_mock_action"]["external_system_created"] is False
    assert len(tools.change_request_calls) == 1

    history = client.get(f"/agent/sessions/{pending['session_id']}").json()
    assert history["approvals"][0]["status"] == "approved"
    assert history["approvals"][0]["result"]["external_system_created"] is False


def test_unknown_and_repeated_approvals_return_http_errors() -> None:
    client, _ = build_test_client()

    assert client.post("/agent/approve/missing").status_code == 404

    pending = client.post(
        "/agent/chat",
        json={"user_message": "Create change request for a synthetic catalogue fix."},
    ).json()
    assert client.post(f"/agent/approve/{pending['approval_id']}").status_code == 200
    assert client.post(f"/agent/approve/{pending['approval_id']}").status_code == 409


def test_unknown_session_returns_not_found() -> None:
    client, _ = build_test_client()

    response = client.get("/agent/sessions/does-not-exist")

    assert response.status_code == 404


def test_chat_reports_retrieval_backend_failure_as_service_unavailable() -> None:
    repository = InMemoryAgentRepository()
    app = create_app(Settings(environment="test", embedding_backend="local_hashing"))

    class UnavailableWorkflow:
        def invoke(self, request):
            raise OSError("embedding backend unavailable")

    app.dependency_overrides[get_agent_repository] = lambda: repository
    app.dependency_overrides[get_agent_workflow] = UnavailableWorkflow

    with TestClient(app) as client:
        response = client.post("/agent/chat", json={"user_message": "Find an API."})

    assert response.status_code == 503
    assert response.json()["detail"] == "Retrieval service is unavailable."


def test_approval_endpoint_traces_decision_and_approved_mock_call() -> None:
    client, _ = build_test_client()
    tracer = RecordingTracer()
    client.app.dependency_overrides[get_observability_tracer] = lambda: tracer
    pending = client.post(
        "/agent/chat",
        json={"user_message": "Create a change request for a synthetic update."},
    ).json()

    response = client.post(f"/agent/approve/{pending['approval_id']}")

    spans = {span.name: span for span in tracer.spans}
    assert response.status_code == 200
    assert (
        spans["agent.human_approval.decision"].attributes["approval.status"]
        == "approved"
    )
    assert spans["agent.mcp"].attributes["tool.name"] == "create_change_request_mock"
