"""Optional OpenTelemetry tracing exported to a local Phoenix collector."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from functools import lru_cache
from typing import Protocol, TypeVar

from app.agent.state import AgentState
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
TraceValue = str | bool | int | float
NodeResult = dict[str, object]
Node = Callable[[AgentState], NodeResult]
T = TypeVar("T")


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


class ExportSpan(TraceSpan, Protocol):
    """Additional OpenTelemetry span capability used for errors."""

    def record_exception(self, error: Exception) -> None:
        """Record an exception observed during instrumented execution."""


class ExportTracer(Protocol):
    """OpenTelemetry tracer behavior consumed by its local adapter."""

    def start_as_current_span(
        self,
        name: str,
        attributes: Mapping[str, TraceValue] | None = None,
    ) -> AbstractContextManager[ExportSpan]:
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
                active_span.record_exception(error)
                active_span.set_attribute("error.type", type(error).__name__)
                raise


def _configured_tracer(settings: Settings) -> AgentTracer:
    if not settings.enable_tracing:
        return NoOpTracer()
    try:
        return _build_otlp_tracer(settings)
    except Exception as error:
        logger.warning(
            "Tracing could not be configured; continuing without trace export: %s",
            error,
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


@lru_cache(maxsize=8)
def _cached_tracer(
    enabled: bool, collector_endpoint: str, app_name: str
) -> AgentTracer:
    return _configured_tracer(
        Settings(
            ENABLE_TRACING=enabled,
            PHOENIX_COLLECTOR_ENDPOINT=collector_endpoint,
            app_name=app_name,
        )
    )


def get_agent_tracer(settings: Settings | None = None) -> AgentTracer:
    """Return an optional configured tracer without contacting Phoenix."""

    configured_settings = settings or get_settings()
    return _cached_tracer(
        configured_settings.enable_tracing,
        configured_settings.phoenix_collector_endpoint,
        configured_settings.app_name,
    )


def traced_node(name: str, node: Node, tracer: AgentTracer) -> Node:
    """Decorate one LangGraph node with non-sensitive outcome attributes."""

    def invoke(state: AgentState) -> NodeResult:
        attributes: dict[str, TraceValue] = {"agent.node": name}
        if name == "mcp" and state["request"].requested_tool is not None:
            attributes["tool.name"] = state["request"].requested_tool.tool_name
        with tracer.span(f"agent.{name}", attributes) as span:
            result = node(state)
            _annotate_node_result(name, result, span)
            return result

    return invoke


def _annotate_node_result(name: str, result: NodeResult, span: TraceSpan) -> None:
    if name == "router" and result.get("route") is not None:
        span.set_attribute("agent.route", str(result["route"]))
    if name == "rag":
        chunks = result.get("retrieved_chunks")
        span.set_attribute("retrieval.result_count", len(chunks) if chunks else 0)
    if name == "mcp":
        calls = result.get("tool_calls")
        span.set_attribute("tool.call_count", len(calls) if calls else 0)
    if name == "human_approval":
        span.set_attribute("approval.status", "pending_human_approval")
        span.set_attribute("approval.required", True)
    if name == "final_answer":
        span.set_attribute("answer.generated", result.get("answer_text") is not None)
