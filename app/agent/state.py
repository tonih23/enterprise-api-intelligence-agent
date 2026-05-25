"""Typed request, state, and response contracts for agent orchestration."""

from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.mcp_server.schemas import ChangeRequestInput
from app.rag.schemas import RetrievedChunk, SearchFilters

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AgentRoute = Literal[
    "answer_with_rag",
    "call_mcp_tool",
    "require_human_approval",
    "ask_clarification",
    "blocked_by_guardrail",
]
ApprovalStatus = Literal["not_required", "pending_human_approval"]
ToolExecutionStatus = Literal["completed", "blocked_pending_approval", "failed"]
GuardrailStatus = Literal[
    "unchecked",
    "passed",
    "blocked",
    "approval_required",
    "clarification_required",
]


class SearchCatalogArguments(BaseModel):
    """Arguments for retrieval through the MCP catalogue tool."""

    model_config = ConfigDict(extra="forbid")

    query: NonEmptyText | None = None
    filters: SearchFilters | None = None


class SearchCatalogToolRequest(BaseModel):
    """Request to invoke synthetic catalogue search."""

    tool_name: Literal["search_api_catalog"]
    arguments: SearchCatalogArguments = Field(default_factory=SearchCatalogArguments)


class GetApiDetailsArguments(BaseModel):
    """Arguments for a synthetic API details lookup."""

    model_config = ConfigDict(extra="forbid")

    api_name: NonEmptyText


class GetApiDetailsToolRequest(BaseModel):
    """Request to load metadata from a local fictional API specification."""

    tool_name: Literal["get_api_details"]
    arguments: GetApiDetailsArguments


class ValidateOpenAPIArguments(BaseModel):
    """Arguments for local structural contract validation."""

    model_config = ConfigDict(extra="forbid")

    spec_path: NonEmptyText


class ValidateOpenAPIToolRequest(BaseModel):
    """Request to validate one local synthetic contract."""

    tool_name: Literal["validate_openapi_spec"]
    arguments: ValidateOpenAPIArguments


class CreateChangeRequestToolRequest(BaseModel):
    """Sensitive mock proposal that cannot execute without approval."""

    tool_name: Literal["create_change_request_mock"]
    arguments: ChangeRequestInput


ToolRequest = Annotated[
    SearchCatalogToolRequest
    | GetApiDetailsToolRequest
    | ValidateOpenAPIToolRequest
    | CreateChangeRequestToolRequest,
    Field(discriminator="tool_name"),
]


class AgentRequest(BaseModel):
    """Input accepted by the deterministic orchestration workflow."""

    model_config = ConfigDict(extra="forbid")

    query: NonEmptyText
    top_k: int = Field(default=5, ge=1, le=20)
    filters: SearchFilters | None = None
    requested_tool: ToolRequest | None = None


class SourceReference(BaseModel):
    """Source evidence disclosed in an agent result."""

    source_path: str
    chunk_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    """Visible record of a completed, blocked, or failed local tool call."""

    tool_name: str
    arguments: dict[str, Any]
    status: ToolExecutionStatus
    result: dict[str, Any] | None = None
    requires_human_approval: bool = False


class AgentResponse(BaseModel):
    """Structured final output returned after graph completion."""

    answer_text: str
    route_taken: AgentRoute
    sources: list[SourceReference] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    approval_status: ApprovalStatus = "not_required"


class AgentState(TypedDict):
    """Shared LangGraph state with explicit fields for every workflow branch."""

    request: AgentRequest
    route: AgentRoute | None
    clarification_prompt: str | None
    retrieved_chunks: list[RetrievedChunk]
    sources: list[SourceReference]
    tool_calls: list[ToolCallRecord]
    approval_status: ApprovalStatus
    guardrail_status: GuardrailStatus
    guardrail_reason: str | None
    draft_answer: str | None
    answer_text: str | None


def initial_state(request: AgentRequest) -> AgentState:
    """Initialize all state fields before invoking the graph."""

    return AgentState(
        request=request,
        route=None,
        clarification_prompt=None,
        retrieved_chunks=[],
        sources=[],
        tool_calls=[],
        approval_status="not_required",
        guardrail_status="unchecked",
        guardrail_reason=None,
        draft_answer=None,
        answer_text=None,
    )


def response_from_state(state: AgentState) -> AgentResponse:
    """Convert completed workflow state into its external response contract."""

    if state["route"] is None or state["answer_text"] is None:
        raise ValueError("Agent graph completed without a route or final answer")
    return AgentResponse(
        answer_text=state["answer_text"],
        route_taken=state["route"],
        sources=state["sources"],
        tool_calls=state["tool_calls"],
        approval_status=state["approval_status"],
    )
