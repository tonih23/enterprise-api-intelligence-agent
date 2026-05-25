"""Simple evaluation contracts and metrics for local agent runs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.state import ToolRequest

ExpectedRoute = Literal["rag", "mcp_tool", "human_approval", "clarification"]


class EvaluationCase(BaseModel):
    """Expected behavior for one synthetic question."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    question: str
    expected_route: ExpectedRoute
    expected_source: str | None = None
    expected_tool_name: str | None = None
    expected_answer_terms: list[str] = Field(default_factory=list)
    requested_tool: ToolRequest | None = None


class EvaluationObservation(BaseModel):
    """Expected and observed behavior for one evaluated question."""

    case_id: str
    expected_route: ExpectedRoute
    actual_route: ExpectedRoute
    expected_source: str | None = None
    actual_sources: list[str] = Field(default_factory=list)
    expected_tool_name: str | None = None
    actual_tool_names: list[str] = Field(default_factory=list)
    expected_answer_terms: list[str] = Field(default_factory=list)
    answer_text: str
    approval_required: bool


class EvaluationMetrics(BaseModel):
    """Aggregate scores for a deterministic evaluation run."""

    route_accuracy: float
    source_recall: float
    tool_call_accuracy: float
    approval_precision: float
    answer_groundedness: float


def _mean(scores: list[float]) -> float:
    return sum(scores) / len(scores) if scores else 1.0


def route_accuracy(observations: list[EvaluationObservation]) -> float:
    """Return the fraction of cases taking the expected graph route."""

    return _mean(
        [
            float(observation.actual_route == observation.expected_route)
            for observation in observations
        ]
    )


def source_recall(observations: list[EvaluationObservation]) -> float:
    """Return recall of explicitly expected evidence documents."""

    scored = [
        float(observation.expected_source in observation.actual_sources)
        for observation in observations
        if observation.expected_source is not None
    ]
    return _mean(scored)


def tool_call_accuracy(observations: list[EvaluationObservation]) -> float:
    """Return selection accuracy for cases expecting an MCP or gated tool."""

    scored = [
        float(observation.expected_tool_name in observation.actual_tool_names)
        for observation in observations
        if observation.expected_tool_name is not None
    ]
    return _mean(scored)


def approval_precision(observations: list[EvaluationObservation]) -> float:
    """Return precision of approval gating among predicted approval cases."""

    predicted = [
        observation for observation in observations if observation.approval_required
    ]
    return _mean(
        [
            float(observation.expected_route == "human_approval")
            for observation in predicted
        ]
    )


def groundedness_for_observation(observation: EvaluationObservation) -> float:
    """Apply a small deterministic groundedness rubric to one answer."""

    normalized_answer = observation.answer_text.lower()
    if observation.expected_route in {"rag", "mcp_tool"}:
        source_supported = (
            observation.expected_source is None
            or observation.expected_source in observation.actual_sources
        )
        terms_supported = all(
            term.lower() in normalized_answer
            for term in observation.expected_answer_terms
        )
        return float(source_supported and terms_supported)
    if observation.expected_route == "human_approval":
        return float(
            observation.approval_required
            and "approval" in normalized_answer
            and "no action has been executed" in normalized_answer
        )
    return float(
        observation.actual_route == "clarification"
        and "please specify" in normalized_answer
    )


def answer_groundedness(observations: list[EvaluationObservation]) -> float:
    """Return average rubric score for source and control-grounded answers."""

    return _mean([groundedness_for_observation(item) for item in observations])


def calculate_metrics(observations: list[EvaluationObservation]) -> EvaluationMetrics:
    """Calculate all aggregate evaluation metrics."""

    return EvaluationMetrics(
        route_accuracy=route_accuracy(observations),
        source_recall=source_recall(observations),
        tool_call_accuracy=tool_call_accuracy(observations),
        approval_precision=approval_precision(observations),
        answer_groundedness=answer_groundedness(observations),
    )
