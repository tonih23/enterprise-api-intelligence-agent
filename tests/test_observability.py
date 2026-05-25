"""Tests for optional, non-disruptive agent tracing."""

from collections.abc import Mapping
from contextlib import contextmanager

from app.agent.graph import AgentWorkflow, create_agent_workflow
from app.agent.state import AgentRequest
from app.config import Settings
from app.observability import phoenix
from app.observability.phoenix import NoOpTracer, TraceValue, get_agent_tracer
from app.rag.schemas import RetrievedChunk, SearchRequest


class FakeRetriever:
    """Return synthetic evidence without any service dependency."""

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="trace-doc",
                text="Synthetic API evidence.",
                score=0.04,
                source_path="data/docs/api_governance_runbook.md",
                metadata={"synthetic": True},
                retrieval_mode="hybrid",
            )
        ]


class RecordedSpan:
    """Collect attributes assigned by workflow instrumentation."""

    def __init__(
        self, name: str, attributes: dict[str, TraceValue] | None = None
    ) -> None:
        self.name = name
        self.attributes = dict(attributes or {})

    def set_attribute(self, key: str, value: TraceValue) -> None:
        self.attributes[key] = value


class RecordingTracer:
    """In-memory tracer used to assert span names and safe metadata."""

    def __init__(self) -> None:
        self.spans: list[RecordedSpan] = []

    @contextmanager
    def span(self, name: str, attributes: Mapping[str, TraceValue] | None = None):
        span = RecordedSpan(name, dict(attributes or {}))
        self.spans.append(span)
        yield span


def test_disabled_tracing_reads_requested_env_toggle_and_is_noop(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_TRACING", "false")
    settings = Settings(_env_file=None)

    tracer = get_agent_tracer(settings)
    response = create_agent_workflow(
        retriever=FakeRetriever(), settings=settings
    ).invoke(AgentRequest(query="Which synthetic endpoint needs approval?"))

    assert settings.enable_tracing is False
    assert isinstance(tracer, NoOpTracer)
    assert response.route_taken == "answer_with_rag"


def test_enable_tracing_supports_unprefixed_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_TRACING", "true")

    settings = Settings(_env_file=None)

    assert settings.enable_tracing is True


def test_tracing_setup_failure_falls_back_to_noop(monkeypatch) -> None:
    def unavailable(settings: Settings):
        raise RuntimeError("collector setup unavailable")

    monkeypatch.setattr(phoenix, "_build_otlp_tracer", unavailable)

    tracer = phoenix._configured_tracer(Settings(_env_file=None, ENABLE_TRACING=True))

    assert isinstance(tracer, NoOpTracer)
    with tracer.span("agent.run"):
        pass


def test_injected_tracer_records_agent_router_retrieval_and_answer_spans() -> None:
    tracer = RecordingTracer()
    response = AgentWorkflow(retriever=FakeRetriever(), tracer=tracer).invoke(
        AgentRequest(query="Which synthetic endpoint needs approval?")
    )

    spans = {span.name: span for span in tracer.spans}
    assert response.route_taken == "answer_with_rag"
    assert set(spans) == {
        "agent.run",
        "agent.router",
        "agent.rag",
        "agent.final_answer",
    }
    assert spans["agent.router"].attributes["agent.route"] == "answer_with_rag"
    assert spans["agent.rag"].attributes["retrieval.result_count"] == 1
    assert spans["agent.run"].attributes["agent.source_count"] == 1
    assert all("query" not in span.attributes for span in tracer.spans)


def test_injected_tracer_records_human_approval_gate() -> None:
    tracer = RecordingTracer()

    response = AgentWorkflow(retriever=FakeRetriever(), tracer=tracer).invoke(
        AgentRequest(query="Create a change request for synthetic API metadata.")
    )

    spans = {span.name: span for span in tracer.spans}
    assert response.approval_status == "pending_human_approval"
    assert spans["agent.human_approval"].attributes["approval.required"] is True
    assert (
        spans["agent.human_approval"].attributes["approval.status"]
        == "pending_human_approval"
    )


def test_injected_tracer_records_local_mcp_tool_dispatch() -> None:
    tracer = RecordingTracer()

    response = AgentWorkflow(retriever=FakeRetriever(), tracer=tracer).invoke(
        AgentRequest(
            query="Read synthetic HCP metadata.",
            requested_tool={
                "tool_name": "get_api_details",
                "arguments": {"api_name": "hcp_search_api"},
            },
        )
    )

    spans = {span.name: span for span in tracer.spans}
    assert response.route_taken == "call_mcp_tool"
    assert spans["agent.mcp"].attributes["tool.name"] == "get_api_details"
    assert spans["agent.mcp"].attributes["tool.call_count"] == 1
