"""Tests for synthetic evaluation metrics and offline execution."""

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.evals.metrics import (
    EvaluationObservation,
    answer_groundedness,
    approval_precision,
    route_accuracy,
    source_recall,
    tool_call_accuracy,
)
from app.evals.run_evals import DEFAULT_DATASET_PATH, load_dataset, run_evaluations


def observation(
    *,
    case_id: str = "case",
    expected_route: str = "rag",
    actual_route: str = "rag",
    expected_source: str | None = "data/docs/source.md",
    actual_sources: list[str] | None = None,
    expected_tool_name: str | None = None,
    actual_tool_names: list[str] | None = None,
    expected_answer_terms: list[str] | None = None,
    answer_text: str = "Grounded source evidence",
    approval_required: bool = False,
) -> EvaluationObservation:
    return EvaluationObservation(
        case_id=case_id,
        expected_route=expected_route,  # type: ignore[arg-type]
        actual_route=actual_route,  # type: ignore[arg-type]
        expected_source=expected_source,
        actual_sources=actual_sources or ["data/docs/source.md"],
        expected_tool_name=expected_tool_name,
        actual_tool_names=actual_tool_names or [],
        expected_answer_terms=expected_answer_terms or [],
        answer_text=answer_text,
        approval_required=approval_required,
    )


def test_route_accuracy_scores_expected_routes() -> None:
    observations = [
        observation(),
        observation(case_id="wrong", actual_route="clarification"),
    ]

    assert route_accuracy(observations) == pytest.approx(0.5)


def test_source_recall_scores_only_cases_with_expected_sources() -> None:
    observations = [
        observation(),
        observation(case_id="missed", actual_sources=["data/docs/other.md"]),
        observation(case_id="not-scored", expected_source=None, actual_sources=[]),
    ]

    assert source_recall(observations) == pytest.approx(0.5)


def test_tool_call_accuracy_includes_gated_tool_selection() -> None:
    observations = [
        observation(
            expected_route="mcp_tool",
            expected_source=None,
            expected_tool_name="get_api_details",
            actual_tool_names=["get_api_details"],
        ),
        observation(
            case_id="gate",
            expected_route="human_approval",
            actual_route="human_approval",
            expected_source=None,
            expected_tool_name="create_change_request_mock",
            actual_tool_names=["create_change_request_mock"],
        ),
    ]

    assert tool_call_accuracy(observations) == pytest.approx(1.0)


def test_approval_precision_penalizes_unnecessary_gating() -> None:
    observations = [
        observation(
            expected_route="human_approval",
            actual_route="human_approval",
            expected_source=None,
            approval_required=True,
        ),
        observation(
            case_id="false-positive",
            expected_route="rag",
            actual_route="human_approval",
            approval_required=True,
        ),
    ]

    assert approval_precision(observations) == pytest.approx(0.5)


def test_answer_groundedness_uses_sources_terms_and_approval_guardrail() -> None:
    observations = [
        observation(
            expected_answer_terms=["evidence"],
            answer_text="Grounded source evidence",
        ),
        observation(
            case_id="approval",
            expected_route="human_approval",
            actual_route="human_approval",
            expected_source=None,
            answer_text="Human approval is required. No action has been executed.",
            approval_required=True,
        ),
    ]

    assert answer_groundedness(observations) == pytest.approx(1.0)


def test_baseline_dataset_contains_twenty_synthetic_routes() -> None:
    dataset = load_dataset(DEFAULT_DATASET_PATH)

    assert len(dataset.cases) == 20
    assert {case.expected_route for case in dataset.cases} == {
        "rag",
        "mcp_tool",
        "human_approval",
        "clarification",
    }


def test_offline_runner_writes_json_result_without_services(tmp_path: Path) -> None:
    result_path = tmp_path / "results.json"

    result = run_evaluations(
        results_path=result_path,
        settings=Settings(_env_file=None, environment="test", ENABLE_TRACING=False),
    )

    saved_result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result.case_count == 20
    assert saved_result["storage_backend"] == "local_json"
    assert saved_result["case_count"] == 20
    assert result.metrics.route_accuracy == pytest.approx(1.0)
