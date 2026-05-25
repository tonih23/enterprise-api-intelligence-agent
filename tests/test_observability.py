"""Tests for optional, non-disruptive agent tracing."""

from collections.abc import Mapping
from contextlib import contextmanager

from app.agent.graph import AgentWorkflow, create_agent_workflow
from app.agent.state import AgentRequest
from app.config import Settings
from app.llm.provider import AnswerSynthesizer
from app.observability import phoenix
from app.observability.langsmith import LangSmithTracer
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


class FakeGeminiProvider:
    """Return safe output without invoking an external provider."""

    model_name = "gemini-2.5-flash"

    def generate(self, prompt: str) -> str:
        return "This synthetic demo evidence describes an API."


def test_default_tracing_backend_is_noop(monkeypatch) -> None:
    monkeypatch.delenv("API_AGENT_TRACING_BACKEND", raising=False)
    monkeypatch.setenv("ENABLE_TRACING", "false")
    settings = Settings(_env_file=None)

    tracer = get_agent_tracer(settings)
    response = create_agent_workflow(
        retriever=FakeRetriever(), settings=settings
    ).invoke(AgentRequest(query="Which synthetic endpoint needs approval?"))

    assert settings.enable_tracing is False
    assert settings.tracing_backend == "none"
    assert settings.effective_tracing_backend == "none"
    assert isinstance(tracer, NoOpTracer)
    assert response.route_taken == "answer_with_rag"


def test_legacy_enable_tracing_selects_phoenix_when_backend_omitted(
    monkeypatch,
) -> None:
    monkeypatch.delenv("API_AGENT_TRACING_BACKEND", raising=False)
    monkeypatch.setenv("ENABLE_TRACING", "true")

    settings = Settings(_env_file=None)

    assert settings.enable_tracing is True
    assert settings.effective_tracing_backend == "phoenix"


def test_explicit_none_backend_disables_legacy_toggle() -> None:
    settings = Settings(
        _env_file=None,
        tracing_backend="none",
        ENABLE_TRACING=True,
    )

    assert settings.effective_tracing_backend == "none"
    assert isinstance(get_agent_tracer(settings), NoOpTracer)


def test_explicit_phoenix_backend_selects_otlp_builder(monkeypatch) -> None:
    expected = RecordingTracer()
    monkeypatch.setattr(phoenix, "_build_otlp_tracer", lambda settings: expected)

    tracer = phoenix._configured_tracer(
        Settings(_env_file=None, tracing_backend="phoenix")
    )

    assert tracer is expected


def test_phoenix_setup_failure_falls_back_to_noop(monkeypatch) -> None:
    def unavailable(settings: Settings):
        raise RuntimeError("collector setup unavailable")

    monkeypatch.setattr(phoenix, "_build_otlp_tracer", unavailable)

    tracer = phoenix._configured_tracer(Settings(_env_file=None, ENABLE_TRACING=True))

    assert isinstance(tracer, NoOpTracer)
    with tracer.span("agent.run"):
        pass


def test_langsmith_backend_selects_managed_builder(monkeypatch) -> None:
    expected = RecordingTracer()
    monkeypatch.setattr(phoenix, "_build_langsmith_tracer", lambda settings: expected)

    tracer = phoenix._configured_tracer(
        Settings(_env_file=None, tracing_backend="langsmith")
    )

    assert tracer is expected


def test_langsmith_missing_api_key_is_noop_without_crashing(
    monkeypatch, caplog
) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "")

    tracer = phoenix._configured_tracer(
        Settings(_env_file=None, tracing_backend="langsmith")
    )

    assert isinstance(tracer, NoOpTracer)
    assert "LANGSMITH_API_KEY is not set" in caplog.text


def test_langsmith_adapter_exports_safe_metadata_without_payloads() -> None:
    captured: dict[str, object] = {}

    class FakeRun:
        def __init__(self, metadata) -> None:
            self.metadata = dict(metadata)

    @contextmanager
    def fake_trace(name, **kwargs):
        captured["name"] = name
        captured.update(kwargs)
        run = FakeRun(kwargs["metadata"])
        captured["run"] = run
        yield run

    tracer = LangSmithTracer(
        client=object(),
        project_name="enterprise-api-intelligence-agent",
        trace_factory=fake_trace,
    )

    with tracer.span(
        "rag.retrieve",
        {
            "data_scope": "synthetic_demo",
            "retrieval_mode": "hybrid",
            "top_k": 5,
            "query": "must-not-export",
        },
    ) as span:
        span.set_attribute("number_of_sources", 2)
        span.set_attribute("prompt", "must-not-export")

    run = captured["run"]
    assert captured["name"] == "rag.retrieve"
    assert captured["inputs"] == {}
    assert captured["metadata"] == {
        "data_scope": "synthetic_demo",
        "retrieval_mode": "hybrid",
        "top_k": 5,
    }
    assert run.metadata["number_of_sources"] == 2
    assert "query" not in run.metadata
    assert "prompt" not in run.metadata
    assert "LANGSMITH_API_KEY" not in run.metadata


def test_langsmith_runtime_failure_does_not_interrupt_workflow() -> None:
    def unavailable_trace(name, **kwargs):
        raise OSError("managed collector unavailable")

    tracer = LangSmithTracer(
        client=object(),
        project_name="enterprise-api-intelligence-agent",
        trace_factory=unavailable_trace,
    )

    with tracer.span("agent.run", {"data_scope": "synthetic_demo"}) as span:
        span.set_attribute("route_taken", "answer_with_rag")


def test_injected_tracer_records_agent_router_retrieval_and_answer_spans() -> None:
    tracer = RecordingTracer()
    response = AgentWorkflow(retriever=FakeRetriever(), tracer=tracer).invoke(
        AgentRequest(query="Which synthetic endpoint needs approval?")
    )

    spans = {span.name: span for span in tracer.spans}
    names = [span.name for span in tracer.spans]
    assert response.route_taken == "answer_with_rag"
    assert set(names) == {
        "agent.run",
        "guardrails.check",
        "router.decide",
        "rag.retrieve",
        "llm.answer_synthesis",
        "final_answer.compose",
    }
    assert names.count("guardrails.check") == 2
    assert spans["router.decide"].attributes["route_taken"] == "answer_with_rag"
    assert spans["rag.retrieve"].attributes["retrieval_mode"] == "hybrid"
    assert spans["rag.retrieve"].attributes["top_k"] == 5
    assert spans["rag.retrieve"].attributes["number_of_sources"] == 1
    assert spans["agent.run"].attributes["number_of_sources"] == 1
    assert spans["agent.run"].attributes["answer_synthesis_mode"] == "deterministic"
    assert spans["llm.answer_synthesis"].attributes["llm_provider"] == "none"
    assert all(
        "query" not in span.attributes
        and "GOOGLE_API_KEY" not in span.attributes
        and span.attributes.get("data_scope") == "synthetic_demo"
        for span in tracer.spans
    )


def test_injected_tracer_records_human_approval_gate() -> None:
    tracer = RecordingTracer()

    response = AgentWorkflow(retriever=FakeRetriever(), tracer=tracer).invoke(
        AgentRequest(query="Create a change request for synthetic API metadata.")
    )

    spans = {span.name: span for span in tracer.spans}
    assert response.approval_status == "pending_human_approval"
    assert spans["approval.gate"].attributes["approval_required"] is True
    assert (
        spans["approval.gate"].attributes["approval_status"] == "pending_human_approval"
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
    assert spans["mcp.tool_call"].attributes["tool_name"] == "get_api_details"
    assert spans["mcp.tool_call"].attributes["tool_call_count"] == 1


def test_synthesis_span_records_mocked_gemini_mode_without_prompt_text() -> None:
    tracer = RecordingTracer()

    AgentWorkflow(
        retriever=FakeRetriever(),
        tracer=tracer,
        answer_synthesizer=AnswerSynthesizer(FakeGeminiProvider()),
    ).invoke(AgentRequest(query="Which synthetic endpoint needs approval?"))

    spans = {span.name: span for span in tracer.spans}
    synthesis = spans["llm.answer_synthesis"].attributes
    assert synthesis["llm_provider"] == "gemini"
    assert synthesis["llm_model"] == "gemini-2.5-flash"
    assert synthesis["answer_synthesis_mode"] == "gemini"
    assert "prompt" not in synthesis
