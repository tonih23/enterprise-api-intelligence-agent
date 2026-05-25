"""Optional metadata-only tracing adapter for managed LangSmith runs."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Protocol

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.observability.phoenix import TraceSpan, TraceValue

logger = logging.getLogger(__name__)
SAFE_METADATA_FIELDS = frozenset(
    {
        "route_taken",
        "retrieval_mode",
        "top_k",
        "number_of_sources",
        "tool_name",
        "approval_status",
        "llm_provider",
        "llm_model",
        "answer_synthesis_mode",
        "data_scope",
        "workflow_step",
        "router_backend",
        "retrieval_result_count",
        "tool_call_count",
        "approval_required",
        "answer_generated",
    }
)


class LangSmithConfigurationError(RuntimeError):
    """Raised when selected LangSmith tracing cannot be configured."""


class _LangSmithCredentials(BaseSettings):
    """Load the LangSmith secret only after this backend is selected."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = Field(
        default=None,
        validation_alias="LANGSMITH_API_KEY",
    )


class LangSmithRun(Protocol):
    """Subset of a LangSmith run needed for safe metadata updates."""

    metadata: dict[str, Any]


TraceFactory = Callable[..., AbstractContextManager[LangSmithRun]]


class LangSmithSpan:
    """Attach only approved scalar metadata fields to a LangSmith run."""

    def __init__(self, run: LangSmithRun) -> None:
        self._run = run

    def set_attribute(self, key: str, value: TraceValue) -> None:
        if key in SAFE_METADATA_FIELDS:
            self._run.metadata[key] = value


class LangSmithTracer:
    """Adapter that creates named LangSmith spans without payload capture."""

    def __init__(
        self,
        *,
        client: object,
        project_name: str,
        trace_factory: TraceFactory | None = None,
    ) -> None:
        self._client = client
        self._project_name = project_name
        self._trace_factory = trace_factory or _trace_context

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Mapping[str, TraceValue] | None = None,
    ) -> Iterator[TraceSpan]:
        """Export safe metadata and never make observability a request dependency."""

        context = None
        try:
            context = self._trace_factory(
                name,
                run_type=_run_type(name),
                inputs={},
                metadata=_safe_metadata(attributes),
                project_name=self._project_name,
                client=self._client,
                tags=["synthetic-demo"],
            )
            run = context.__enter__()
        except Exception as error:
            logger.warning(
                "LangSmith span could not start; continuing without export: %s",
                type(error).__name__,
            )
            yield _DiscardSpan()
            return

        try:
            yield LangSmithSpan(run)
        except Exception:
            _close_context(context)
            raise
        else:
            _close_context(context)


class _DiscardSpan:
    def set_attribute(self, key: str, value: TraceValue) -> None:
        """Discard attributes after non-critical trace setup failure."""


def _safe_metadata(
    attributes: Mapping[str, TraceValue] | None,
) -> dict[str, TraceValue]:
    return {
        key: value
        for key, value in (attributes or {}).items()
        if key in SAFE_METADATA_FIELDS
    }


def _close_context(context: AbstractContextManager[LangSmithRun]) -> None:
    try:
        context.__exit__(None, None, None)
    except Exception as error:
        logger.warning(
            "LangSmith span could not finish; continuing without export: %s",
            type(error).__name__,
        )


def _run_type(name: str) -> str:
    if name == "llm.answer_synthesis":
        return "llm"
    if name == "mcp.tool_call":
        return "tool"
    return "chain"


def _trace_context(*args: Any, **kwargs: Any) -> AbstractContextManager[LangSmithRun]:
    from langsmith.run_helpers import trace

    return trace(*args, **kwargs)


def build_langsmith_tracer(project_name: str) -> LangSmithTracer:
    """Build the managed tracer only when an API key has been supplied."""

    configured_key = _LangSmithCredentials().api_key
    api_key = configured_key.get_secret_value() if configured_key else None
    if not api_key:
        raise LangSmithConfigurationError(
            "LANGSMITH_API_KEY is not set; LangSmith tracing is disabled."
        )

    from langsmith import Client

    return LangSmithTracer(client=Client(api_key=api_key), project_name=project_name)
