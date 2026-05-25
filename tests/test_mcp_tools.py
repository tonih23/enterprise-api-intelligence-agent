"""Unit tests for local synthetic MCP tool logic."""

import json
from pathlib import Path

from app.mcp_server.tools import McpToolService
from app.rag.schemas import RetrievedChunk, SearchFilters, SearchRequest

DATA_ROOT = Path(__file__).parents[1] / "data"


class FakeRetriever:
    """Return stable evidence and record the RAG request made by the tool."""

    def __init__(self) -> None:
        self.requests: list[SearchRequest] = []

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        self.requests.append(request)
        return [
            RetrievedChunk(
                chunk_id="catalog-chunk",
                text="POST /trial-interest-requests requires approval.",
                score=0.03,
                source_path="data/docs/fake_mulesoft_api_catalogue.md",
                metadata={"api_name": "clinical_trials_api"},
                retrieval_mode="hybrid",
            )
        ]


def test_search_api_catalog_delegates_to_hybrid_rag_with_filters() -> None:
    retriever = FakeRetriever()
    service = McpToolService(retriever=retriever, data_root=DATA_ROOT)
    filters = SearchFilters(api_name="clinical_trials_api")

    result = service.search_api_catalog("Which operation needs approval?", filters)

    request = retriever.requests[0]
    assert request.mode == "hybrid"
    assert request.top_k == 5
    assert request.filters == filters
    assert result.search.results[0].chunk_id == "catalog-chunk"
    assert result.policy.requires_human_approval is False


def test_get_api_details_reads_synthetic_openapi_operations() -> None:
    service = McpToolService(data_root=DATA_ROOT)

    details = service.get_api_details("clinical_trials_api")

    approval_operation = next(
        operation
        for operation in details.operations
        if operation.path == "/trial-interest-requests"
    )
    assert details.version == "2.1.0"
    assert details.metadata["synthetic"] is True
    assert details.source_path == "data/api_specs/clinical_trials_api.openapi.yaml"
    assert approval_operation.method == "POST"
    assert approval_operation.requires_human_approval is True


def test_validate_openapi_spec_accepts_local_synthetic_contract() -> None:
    service = McpToolService(data_root=DATA_ROOT)

    result = service.validate_openapi_spec("hcp_search_api.openapi.yaml")

    assert result.valid is True
    assert result.errors == []
    assert result.api_name == "hcp_search_api"
    assert result.spec_path == "data/api_specs/hcp_search_api.openapi.yaml"


def test_validate_openapi_spec_rejects_paths_outside_synthetic_specs() -> None:
    service = McpToolService(data_root=DATA_ROOT)

    result = service.validate_openapi_spec("../docs/api_governance_runbook.md")

    assert result.valid is False
    assert "inside data/api_specs" in result.errors[0]


def test_validate_openapi_spec_reports_basic_structure_errors(tmp_path: Path) -> None:
    specs_root = tmp_path / "data" / "api_specs"
    specs_root.mkdir(parents=True)
    (specs_root / "incomplete.yaml").write_text(
        "openapi: 3.1.0\ninfo:\n  title: Synthetic Incomplete API\npaths: {}\n",
        encoding="utf-8",
    )
    service = McpToolService(data_root=tmp_path / "data")

    result = service.validate_openapi_spec("incomplete.yaml")

    assert result.valid is False
    assert "info.version is required" in result.errors
    assert "paths must contain at least one operation" in result.errors


def test_validate_openapi_spec_accepts_local_json_contract(tmp_path: Path) -> None:
    specs_root = tmp_path / "data" / "api_specs"
    specs_root.mkdir(parents=True)
    (specs_root / "synthetic_api.json").write_text(
        json.dumps(
            {
                "openapi": "3.1.0",
                "info": {
                    "title": "Synthetic JSON API",
                    "version": "1.0.0",
                    "x-agent-metadata": {
                        "synthetic": True,
                        "domain": "api_enablement",
                        "owner": "fictional_owner",
                        "data_classification": "synthetic_internal",
                        "system": "fictional_system",
                        "api_name": "synthetic_json_api",
                        "version": "1.0.0",
                    },
                },
                "paths": {"/examples": {"get": {"summary": "List examples"}}},
            }
        ),
        encoding="utf-8",
    )
    service = McpToolService(data_root=tmp_path / "data")

    result = service.validate_openapi_spec("synthetic_api.json")

    assert result.valid is True
    assert result.api_name == "synthetic_json_api"


def test_create_change_request_mock_is_pending_and_has_no_side_effects() -> None:
    service = McpToolService(data_root=DATA_ROOT)

    first = service.create_change_request_mock(
        "Promote trials schema", "Add a fictional status filter.", "high"
    )
    second = service.create_change_request_mock(
        "Promote trials schema", "Add a fictional status filter.", "high"
    )

    assert first == second
    assert first.change_request_id.startswith("CR-MOCK-")
    assert first.status == "pending_human_approval"
    assert first.requires_human_approval is True
    assert first.external_system_created is False
    assert first.policy.requires_human_approval is True
    assert first.policy.side_effects is False
