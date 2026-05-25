"""Optional tracer selection and Phoenix OpenTelemetry implementation."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol, TypeVar

from app.agent.state import AgentState
from app.config import Settings, get_settings
from app.llm.schemas import AnswerSynthesisStatus

logger = logging.getLogger(__name__)
TraceValue = str | bool | int | float
NodeResult = dict[str, object]
Node = Callable[[AgentState], NodeResult]
T = TypeVar("T")
NODE_SPAN_NAMES = {
    "request_guardrails": "guardrails.check",
    "tool_guardrails": "guardrails.check",
    "final_guardrails": "guardrails.check",
    "router": "router.decide",
    "rag": "rag.retrieve",
    "mcp": "mcp.tool_call",
    "human_approval": "approval.gate",
    "final_answer": "final_answer.compose",
}


class TraceSpan(Protocol):
    """Minimal span behavior consumed by application instrumentation."""

    def set_attribute(self, key: str, value: TraceValue) -> None:
        """Record low-cardinality, non-sensitive execution metadata."""


class AgentTracer(Protocol):
    """Tracing interface implemented by no-op and OpenTelemetry tracers."""

    def span(
        self,
        name: str,
        attributes: Mapping[str, TraceValue] | None = None,
    ) -> AbstractContextManager[TraceSpan]:
        """Create one trace span around a unit of workflow work."""


class ExportTracer(Protocol):
    """OpenTelemetry tracer behavior consumed by its local adapter."""

    def start_as_current_span(
        self,
        name: str,
        attributes: Mapping[str, TraceValue] | None = None,
    ) -> AbstractContextManager[TraceSpan]:
        """Begin an OpenTelemetry span context."""


class NoOpSpan:
    """Discard trace attributes while preserving the instrumentation contract."""

    def set_attribute(self, key: str, value: TraceValue) -> None:
        """Ignore an attribute when tracing is disabled."""


class NoOpTracer:
    """No-network tracer used by default and after setup failures."""

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Mapping[str, TraceValue] | None = None,
    ) -> Iterator[TraceSpan]:
        """Yield a harmless span without exporting anything."""

        yield NoOpSpan()


class OpenTelemetryTracer:
    """Thin adapter over an OpenTelemetry tracer instance."""

    def __init__(self, tracer: ExportTracer) -> None:
        self._tracer = tracer

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Mapping[str, TraceValue] | None = None,
    ) -> Iterator[TraceSpan]:
        """Start a span and preserve application errors for graph callers."""

        with self._tracer.start_as_current_span(
            name, attributes=dict(attributes or {})
        ) as active_span:
            try:
                yield active_span
            except Exception as error:
                active_span.set_attribute("error.type", type(error).__name__)
                raise


def _configured_tracer(settings: Settings) -> AgentTracer:
    backend = settings.effective_tracing_backend
    if backend == "none":
        return NoOpTracer()
    try:
        if backend == "phoenix":
            return _build_otlp_tracer(settings)
        return _build_langsmith_tracer(settings)
    except Exception as error:
        detail = (
            str(error)
            if type(error).__name__ == "LangSmithConfigurationError"
            else type(error).__name__
        )
        logger.warning(
            "%s tracing could not be configured; continuing without trace export: %s",
            backend.capitalize(),
            detail,
        )
        return NoOpTracer()


def _build_otlp_tracer(settings: Settings) -> AgentTracer:
    """Configure local OTLP/HTTP export for a running Phoenix collector."""

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: settings.app_name})
    )
    exporter = OTLPSpanExporter(endpoint=settings.phoenix_collector_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return OpenTelemetryTracer(provider.get_tracer("app.agent"))


def _build_langsmith_tracer(settings: Settings) -> AgentTracer:
    """Configure managed LangSmith tracing only when selected."""

    from app.observability.langsmith import build_langsmith_tracer

    return build_langsmith_tracer(settings.langsmith_project)


def get_agent_tracer(settings: Settings | None = None) -> AgentTracer:
    """Return the selected optional tracer without exporting application payloads."""

    configured_settings = settings or get_settings()
    return _configured_tracer(configured_settings)


def traced_node(name: str, node: Node, tracer: AgentTracer) -> Node:
    """Decorate one LangGraph node with non-sensitive outcome attributes."""

    def invoke(state: AgentState) -> NodeResult:
        attributes: dict[str, TraceValue] = {
            "workflow_step": name,
            "data_scope": "synthetic_demo",
        }
        if name == "rag":
            attributes["retrieval_mode"] = state["request"].mode
            attributes["top_k"] = state["request"].top_k
        if (
            name in {"mcp", "tool_guardrails"}
            and state["request"].requested_tool is not None
        ):
            attributes["tool_name"] = state["request"].requested_tool.tool_name
        if name == "final_answer" and state["route"] is not None:
            attributes["route_taken"] = state["route"]
            attributes["number_of_sources"] = len(state["sources"])
            attributes["approval_status"] = state["approval_status"]
        with tracer.span(NODE_SPAN_NAMES[name], attributes) as span:
            result = node(state)
            _annotate_node_result(name, result, span)
            return result

    return invoke


def _annotate_node_result(name: str, result: NodeResult, span: TraceSpan) -> None:
    if name == "router" and result.get("route") is not None:
        span.set_attribute("route_taken", str(result["route"]))
    if name == "rag":
        chunks = result.get("retrieved_chunks")
        sources = result.get("sources")
        span.set_attribute("retrieval_result_count", len(chunks) if chunks else 0)
        span.set_attribute("number_of_sources", len(sources) if sources else 0)
    if name == "mcp":
        calls = result.get("tool_calls")
        sources = result.get("sources")
        span.set_attribute("tool_call_count", len(calls) if calls else 0)
        span.set_attribute("number_of_sources", len(sources) if sources else 0)
    if name == "human_approval":
        span.set_attribute("approval_status", "pending_human_approval")
        span.set_attribute("approval_required", True)
    if name == "final_answer":
        span.set_attribute("answer_generated", result.get("answer_text") is not None)
        synthesis = result.get("answer_synthesis")
        if isinstance(synthesis, AnswerSynthesisStatus):
            span.set_attribute("answer_synthesis_mode", synthesis.mode)
            span.set_attribute("llm_provider", synthesis.provider)
            if synthesis.model:
                span.set_attribute("llm_model", synthesis.model)
