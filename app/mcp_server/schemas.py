"""Structured input and output contracts for local MCP tools."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.rag.schemas import SearchResponse

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RiskLevel = Literal["low", "medium", "high"]


class ToolPolicy(BaseModel):
    """Governance metadata communicated alongside a tool result."""

    risk_level: RiskLevel
    requires_human_approval: bool
    side_effects: bool


class CatalogSearchResult(BaseModel):
    """Hybrid retrieval evidence returned by catalogue search."""

    search: SearchResponse
    policy: ToolPolicy = ToolPolicy(
        risk_level="low",
        requires_human_approval=False,
        side_effects=False,
    )


class ApiOperation(BaseModel):
    """Operation summary extracted from a fictional OpenAPI contract."""

    method: str
    path: str
    operation_id: str | None = None
    summary: str | None = None
    requires_human_approval: bool = False


class ApiDetails(BaseModel):
    """Metadata and operations for one synthetic API specification."""

    api_name: str
    title: str
    version: str
    description: str | None = None
    source_path: str
    metadata: dict[str, object]
    server_urls: list[str]
    operations: list[ApiOperation]
    policy: ToolPolicy = ToolPolicy(
        risk_level="low",
        requires_human_approval=False,
        side_effects=False,
    )


class OpenAPIValidationResult(BaseModel):
    """Basic structural validation result for a local synthetic contract."""

    spec_path: str
    valid: bool
    errors: list[str] = Field(default_factory=list)
    api_name: str | None = None
    version: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    policy: ToolPolicy = ToolPolicy(
        risk_level="low",
        requires_human_approval=False,
        side_effects=False,
    )


class ChangeRequestInput(BaseModel):
    """Arguments for a simulated governance change request."""

    model_config = ConfigDict(extra="forbid")

    title: NonEmptyText
    description: NonEmptyText
    risk_level: RiskLevel


class MockChangeRequest(BaseModel):
    """A non-executing change proposal that must remain approval-gated."""

    change_request_id: str
    title: str
    description: str
    risk_level: RiskLevel
    status: Literal["pending_human_approval", "approved"] = "pending_human_approval"
    synthetic: Literal[True] = True
    mock: Literal[True] = True
    requires_human_approval: Literal[True] = True
    external_system_created: Literal[False] = False
    policy: ToolPolicy = ToolPolicy(
        risk_level="medium",
        requires_human_approval=True,
        side_effects=False,
    )
