"""Execute deterministic agent evaluations over the local synthetic corpus."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.agent.graph import create_agent_workflow
from app.agent.state import AgentRequest, AgentResponse
from app.config import Settings
from app.evals.metrics import (
    EvaluationCase,
    EvaluationMetrics,
    EvaluationObservation,
    ExpectedRoute,
    calculate_metrics,
)
from app.mcp_server.tools import McpToolService
from app.rag.chunking import SourceDocument, load_documents
from app.rag.schemas import RetrievedChunk, SearchRequest

PROJECT_ROOT = Path(__file__).parents[2]
DEFAULT_DATASET_PATH = Path(__file__).with_name("test_set.yaml")
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "artifacts" / "evals" / "latest.json"
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data"
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_ROUTE_LABELS: dict[str, ExpectedRoute] = {
    "answer_with_rag": "rag",
    "call_mcp_tool": "mcp_tool",
    "require_human_approval": "human_approval",
    "ask_clarification": "clarification",
}


class EvaluationDataset(BaseModel):
    """Versioned list of fictional questions and expected behavior."""

    name: str
    description: str
    cases: list[EvaluationCase]


class EvaluationRunResult(BaseModel):
    """Serializable local result artifact for one evaluation execution."""

    dataset_name: str
    executed_at: datetime
    case_count: int
    metrics: EvaluationMetrics
    observations: list[EvaluationObservation] = Field(default_factory=list)
    storage_backend: str = "local_json"


class OfflineSyntheticRetriever:
    """Deterministic lexical baseline over local fictional source documents."""

    def __init__(self, documents: list[SourceDocument]) -> None:
        self.documents = documents

    @classmethod
    def from_data_root(
        cls, data_root: Path = DEFAULT_DATA_ROOT
    ) -> OfflineSyntheticRetriever:
        """Load the local synthetic corpus without OpenSearch or embeddings."""

        return cls(load_documents(data_root))

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        """Rank full documents by token overlap for reproducible eval execution."""

        query_terms = _tokenize(request.query)
        candidates: list[tuple[float, SourceDocument]] = []
        filters = (
            request.filters.model_dump(exclude_none=True) if request.filters else {}
        )
        for document in self.documents:
            if any(
                document.metadata.get(key) != value for key, value in filters.items()
            ):
                continue
            document_terms = _tokenize(document.text) | _tokenize(document.source_path)
            overlap = query_terms & document_terms
            if not overlap:
                continue
            score = float(len(overlap)) / float(max(len(query_terms), 1))
            candidates.append((score, document))

        candidates.sort(key=lambda item: (-item[0], item[1].source_path))
        return [
            RetrievedChunk(
                chunk_id=f"eval::{document.source_path}",
                text=document.text,
                score=score,
                source_path=document.source_path,
                metadata=document.metadata,
                retrieval_mode=request.mode,
            )
            for score, document in candidates[: request.top_k]
        ]


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def load_dataset(path: Path = DEFAULT_DATASET_PATH) -> EvaluationDataset:
    """Load and validate the checked-in synthetic evaluation set."""

    raw_dataset = yaml.safe_load(path.read_text(encoding="utf-8"))
    dataset = EvaluationDataset.model_validate(raw_dataset)
    if len(dataset.cases) != 20:
        raise ValueError(
            "The baseline evaluation dataset must contain exactly 20 cases"
        )
    return dataset


def _agent_request(case: EvaluationCase) -> AgentRequest:
    return AgentRequest(query=case.question, requested_tool=case.requested_tool)


def _observation(
    case: EvaluationCase, response: AgentResponse
) -> EvaluationObservation:
    return EvaluationObservation(
        case_id=case.case_id,
        expected_route=case.expected_route,
        actual_route=_ROUTE_LABELS[response.route_taken],
        expected_source=case.expected_source,
        actual_sources=[source.source_path for source in response.sources],
        expected_tool_name=case.expected_tool_name,
        actual_tool_names=[call.tool_name for call in response.tool_calls],
        expected_answer_terms=case.expected_answer_terms,
        answer_text=response.answer_text,
        approval_required=response.approval_status == "pending_human_approval",
    )


def run_evaluations(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    results_path: Path = DEFAULT_RESULTS_PATH,
    data_root: Path = DEFAULT_DATA_ROOT,
    settings: Settings | None = None,
) -> EvaluationRunResult:
    """Run all cases through the real graph with an offline synthetic retriever."""

    dataset = load_dataset(dataset_path)
    retriever = OfflineSyntheticRetriever.from_data_root(data_root)
    tools = McpToolService(retriever=retriever, data_root=data_root)
    configured_settings = settings or Settings()
    workflow = create_agent_workflow(
        retriever=retriever,
        mcp_tools=tools,
        settings=configured_settings,
    )
    observations = [
        _observation(case, workflow.invoke(_agent_request(case)))
        for case in dataset.cases
    ]
    result = EvaluationRunResult(
        dataset_name=dataset.name,
        executed_at=datetime.now(UTC),
        case_count=len(observations),
        metrics=calculate_metrics(observations),
        observations=observations,
    )
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    """Run local evaluations and print concise aggregate scores."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS_PATH)
    args = parser.parse_args()
    result = run_evaluations(dataset_path=args.dataset, results_path=args.output)
    print(f"Evaluated {result.case_count} synthetic cases: {args.output}")
    print(json.dumps(result.metrics.model_dump(), indent=2))


if __name__ == "__main__":
    main()
