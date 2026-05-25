"""Framework-independent tool logic over synthetic project artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

import yaml

from app.mcp_server.schemas import (
    ApiDetails,
    ApiOperation,
    CatalogSearchResult,
    ChangeRequestInput,
    MockChangeRequest,
    OpenAPIValidationResult,
    RiskLevel,
)
from app.rag.chunking import REQUIRED_METADATA_FIELDS
from app.rag.schemas import RetrievedChunk, SearchFilters, SearchRequest, SearchResponse

DEFAULT_DATA_ROOT = Path(__file__).parents[2] / "data"


class CatalogRetriever(Protocol):
    """Search interface required by the catalogue MCP tool."""

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        """Return indexed evidence chunks for a validated search request."""


class McpToolService:
    """Execute local MCP-facing capabilities without external side effects."""

    def __init__(
        self,
        *,
        retriever: CatalogRetriever | None = None,
        data_root: Path = DEFAULT_DATA_ROOT,
    ) -> None:
        self.retriever = retriever
        self.data_root = data_root
        self.specs_root = (data_root / "api_specs").resolve()

    def search_api_catalog(
        self, query: str, filters: SearchFilters | None = None
    ) -> CatalogSearchResult:
        """Search indexed synthetic documentation through existing hybrid RAG."""

        if self.retriever is None:
            raise RuntimeError("search_api_catalog requires a configured retriever")
        request = SearchRequest(
            query=query,
            top_k=5,
            mode="hybrid",
            filters=filters,
        )
        results = self.retriever.search(request)
        return CatalogSearchResult(
            search=SearchResponse(
                query=request.query, mode=request.mode, results=results
            )
        )

    def get_api_details(self, api_name: str) -> ApiDetails:
        """Extract metadata and operations for a named synthetic OpenAPI API."""

        for path in sorted(self.specs_root.glob("*.openapi.*")):
            specification = self._read_structured_file(path)
            metadata = self._extract_metadata(specification)
            if metadata.get("api_name") == api_name:
                return self._build_api_details(path, specification, metadata)
        raise ValueError(f"Synthetic API not found: {api_name}")

    def validate_openapi_spec(self, spec_path: str) -> OpenAPIValidationResult:
        """Validate basic OpenAPI structure only within the local synthetic corpus."""

        try:
            path = self._resolve_spec_path(spec_path)
        except ValueError as error:
            return OpenAPIValidationResult(
                spec_path=spec_path, valid=False, errors=[str(error)]
            )

        try:
            specification = self._read_structured_file(path)
        except (OSError, ValueError, yaml.YAMLError) as error:
            return OpenAPIValidationResult(
                spec_path=self._display_path(path),
                valid=False,
                errors=[f"Unable to parse specification: {error}"],
            )

        errors: list[str] = []
        if not str(specification.get("openapi", "")).startswith("3."):
            errors.append("openapi must declare version 3.x")
        info = specification.get("info")
        if not isinstance(info, dict):
            errors.append("info must be an object")
            info = {}
        if not info.get("title"):
            errors.append("info.title is required")
        if not info.get("version"):
            errors.append("info.version is required")
        metadata = self._extract_metadata(specification)
        missing_metadata = REQUIRED_METADATA_FIELDS - metadata.keys()
        if missing_metadata:
            errors.append(
                "info.x-agent-metadata is missing: "
                + ", ".join(sorted(missing_metadata))
            )
        if metadata.get("synthetic") is not True:
            errors.append("info.x-agent-metadata.synthetic must be true")
        paths = specification.get("paths")
        if not isinstance(paths, dict) or not paths:
            errors.append("paths must contain at least one operation")

        return OpenAPIValidationResult(
            spec_path=self._display_path(path),
            valid=not errors,
            errors=errors,
            api_name=metadata.get("api_name"),
            version=info.get("version"),
            metadata=metadata,
        )

    def create_change_request_mock(
        self, title: str, description: str, risk_level: RiskLevel
    ) -> MockChangeRequest:
        """Return a simulated pending change request without making a write."""

        request = ChangeRequestInput(
            title=title, description=description, risk_level=risk_level
        )
        digest = hashlib.sha256(
            f"{request.title}:{request.description}:{request.risk_level}".encode()
        ).hexdigest()[:12]
        policy_risk = "medium" if request.risk_level == "low" else request.risk_level
        return MockChangeRequest(
            change_request_id=f"CR-MOCK-{digest.upper()}",
            title=request.title,
            description=request.description,
            risk_level=request.risk_level,
            policy={
                "risk_level": policy_risk,
                "requires_human_approval": True,
                "side_effects": False,
            },
        )

    def _resolve_spec_path(self, spec_path: str) -> Path:
        raw_path = Path(spec_path)
        if raw_path.is_absolute():
            candidate = raw_path.resolve()
        elif raw_path.parts and raw_path.parts[0] == "data":
            candidate = (self.data_root.parent / raw_path).resolve()
        else:
            candidate = (self.specs_root / raw_path).resolve()

        if not candidate.is_relative_to(self.specs_root):
            raise ValueError("Specification must be inside data/api_specs")
        if candidate.suffix.lower() not in {".json", ".yaml", ".yml"}:
            raise ValueError("Specification must be a JSON or YAML file")
        if not candidate.is_file():
            raise ValueError("Specification file does not exist")
        return candidate

    def _read_structured_file(self, path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        document = (
            json.loads(content)
            if path.suffix.lower() == ".json"
            else yaml.safe_load(content)
        )
        if not isinstance(document, dict):
            raise ValueError(f"{path} does not contain an object specification")
        return document

    def _display_path(self, path: Path) -> str:
        return (Path(self.data_root.name) / path.relative_to(self.data_root)).as_posix()

    @staticmethod
    def _extract_metadata(specification: dict[str, Any]) -> dict[str, Any]:
        info = specification.get("info", {})
        if not isinstance(info, dict):
            return {}
        metadata = info.get("x-agent-metadata", {})
        return dict(metadata) if isinstance(metadata, dict) else {}

    def _build_api_details(
        self,
        path: Path,
        specification: dict[str, Any],
        metadata: dict[str, Any],
    ) -> ApiDetails:
        info = specification["info"]
        operations = []
        for endpoint, path_item in specification.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                operations.append(
                    ApiOperation(
                        method=method.upper(),
                        path=endpoint,
                        operation_id=operation.get("operationId"),
                        summary=operation.get("summary"),
                        requires_human_approval=operation.get(
                            "x-human-approval-required", False
                        ),
                    )
                )
        return ApiDetails(
            api_name=str(metadata["api_name"]),
            title=str(info["title"]),
            version=str(info["version"]),
            description=info.get("description"),
            source_path=self._display_path(path),
            metadata=metadata,
            server_urls=[
                server["url"]
                for server in specification.get("servers", [])
                if isinstance(server, dict) and "url" in server
            ],
            operations=operations,
        )
