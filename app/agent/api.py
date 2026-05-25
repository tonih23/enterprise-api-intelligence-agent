"""HTTP endpoints exposing the deterministic local agent workflow."""

from __future__ import annotations

import re
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from opensearchpy.exceptions import OpenSearchException
from pydantic import BaseModel, ConfigDict, Field

from app.agent.graph import AgentWorkflow, create_agent_workflow
from app.agent.repository import (
    AgentRepository,
    ApprovalRecord,
    SessionRecord,
    get_agent_repository,
)
from app.agent.state import (
    AgentRequest,
    AgentResponse,
    AgentRoute,
    ApprovalStatus,
    NonEmptyText,
    SourceReference,
    ToolCallRecord,
)
from app.config import Settings, get_settings
from app.mcp_server.schemas import ChangeRequestInput, MockChangeRequest
from app.mcp_server.tools import McpToolService
from app.rag.retriever import RagRetriever, get_retriever

router = APIRouter(prefix="/agent", tags=["agent"])
_GET_DETAILS = re.compile(
    r"^(?:get|show)\s+api\s+details\s+(?:for\s+)?(?P<api_name>[\w-]+)[?.]?$",
    re.IGNORECASE,
)
_VALIDATE_SPEC = re.compile(
    r"^validate\s+(?:openapi\s+spec\s+)?(?P<spec_path>[\w./-]+\.(?:json|ya?ml))[?.]?$",
    re.IGNORECASE,
)
_SEARCH_CATALOG = re.compile(
    r"^search\s+(?:the\s+)?api\s+catalog(?:ue)?\s+for\s+(?P<query>.+)$",
    re.IGNORECASE,
)


class ChatRequest(BaseModel):
    """Chat input accepted by the agent API."""

    model_config = ConfigDict(extra="forbid")

    user_message: NonEmptyText
    session_id: NonEmptyText | None = None


class ChatResponse(BaseModel):
    """Graph result decorated with session and approval identifiers."""

    final_answer: str
    route_taken: AgentRoute
    sources: list[SourceReference] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    approval_status: ApprovalStatus
    session_id: str
    approval_id: str | None = None


class SessionTurnResponse(BaseModel):
    """Basic conversation metadata returned for session history."""

    user_message: str
    final_answer: str
    route_taken: AgentRoute
    approval_status: ApprovalStatus
    approval_id: str | None = None


class SessionApprovalResponse(BaseModel):
    """Approval status retained in session history."""

    approval_id: str
    status: Literal["pending_human_approval", "approved"]
    request: ChangeRequestInput
    result: MockChangeRequest | None = None


class SessionHistoryResponse(BaseModel):
    """Recorded local interaction and approval history."""

    session_id: str
    messages: list[SessionTurnResponse]
    approvals: list[SessionApprovalResponse]


class ApprovalResponse(BaseModel):
    """Successful simulated approval response."""

    approval_id: str
    session_id: str
    approval_status: Literal["approved"] = "approved"
    final_answer: str
    tool_calls: list[ToolCallRecord]
    approved_mock_action: MockChangeRequest


def get_agent_workflow(
    settings: Annotated[Settings, Depends(get_settings)],
    retriever: Annotated[RagRetriever, Depends(get_retriever)],
) -> AgentWorkflow:
    """Build an agent workflow backed by configured local services."""

    return create_agent_workflow(retriever=retriever, settings=settings)


def get_approval_tools() -> McpToolService:
    """Return local synthetic-only tools used after explicit approval."""

    return McpToolService()


def _session_id(provided_session_id: str | None) -> str:
    return provided_session_id or f"session_{uuid4().hex}"


def _request_from_message(user_message: str) -> AgentRequest:
    """Map a few explicit local tool commands; otherwise use normal routing."""

    match = _GET_DETAILS.match(user_message)
    if match:
        return AgentRequest(
            query=user_message,
            requested_tool={
                "tool_name": "get_api_details",
                "arguments": {"api_name": match.group("api_name")},
            },
        )
    match = _VALIDATE_SPEC.match(user_message)
    if match:
        return AgentRequest(
            query=user_message,
            requested_tool={
                "tool_name": "validate_openapi_spec",
                "arguments": {"spec_path": match.group("spec_path")},
            },
        )
    match = _SEARCH_CATALOG.match(user_message)
    if match:
        return AgentRequest(
            query=user_message,
            requested_tool={
                "tool_name": "search_api_catalog",
                "arguments": {"query": match.group("query").rstrip("?.")},
            },
        )
    return AgentRequest(query=user_message)


def _pending_approval_input(result: AgentResponse) -> ChangeRequestInput:
    blocked_call = next(
        (
            call
            for call in result.tool_calls
            if call.status == "blocked_pending_approval"
            and call.tool_name == "create_change_request_mock"
        ),
        None,
    )
    if blocked_call is None:
        raise RuntimeError("Approval route did not include a pending mock action")
    return ChangeRequestInput.model_validate(blocked_call.arguments)


def _chat_response(
    *,
    session_id: str,
    result: AgentResponse,
    approval: ApprovalRecord | None,
) -> ChatResponse:
    return ChatResponse(
        final_answer=result.answer_text,
        route_taken=result.route_taken,
        sources=result.sources,
        tool_calls=result.tool_calls,
        approval_status=result.approval_status,
        session_id=session_id,
        approval_id=approval.approval_id if approval else None,
    )


@router.post("/chat", response_model=ChatResponse, summary="Run an agent turn")
def chat(
    request: ChatRequest,
    workflow: Annotated[AgentWorkflow, Depends(get_agent_workflow)],
    repository: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> ChatResponse:
    """Route one user message through the deterministic graph."""

    session_id = _session_id(request.session_id)
    try:
        result = workflow.invoke(_request_from_message(request.user_message))
    except OpenSearchException as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent retrieval service is unavailable.",
        ) from error

    approval = None
    if result.approval_status == "pending_human_approval":
        approval = repository.create_approval(
            session_id=session_id,
            request=_pending_approval_input(result),
        )
    repository.add_turn(
        session_id=session_id,
        user_message=request.user_message,
        response=result,
        approval_id=approval.approval_id if approval else None,
    )
    return _chat_response(session_id=session_id, result=result, approval=approval)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionHistoryResponse,
    summary="Get local agent session history",
)
def session_history(
    session_id: str,
    repository: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> SessionHistoryResponse:
    """Return basic conversation and approval metadata for a local session."""

    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    return _session_response(session)


def _session_response(session: SessionRecord) -> SessionHistoryResponse:
    return SessionHistoryResponse(
        session_id=session.session_id,
        messages=[
            SessionTurnResponse(
                user_message=turn.user_message,
                final_answer=turn.response.answer_text,
                route_taken=turn.response.route_taken,
                approval_status=turn.response.approval_status,
                approval_id=turn.approval_id,
            )
            for turn in session.turns
        ],
        approvals=[
            SessionApprovalResponse(
                approval_id=approval.approval_id,
                status=approval.status,
                request=approval.request,
                result=approval.result,
            )
            for approval in session.approvals
        ],
    )


@router.post(
    "/approve/{approval_id}",
    response_model=ApprovalResponse,
    summary="Approve a pending mock action",
)
def approve(
    approval_id: str,
    repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    tools: Annotated[McpToolService, Depends(get_approval_tools)],
) -> ApprovalResponse:
    """Simulate approval, then run only the local mock action."""

    approval = repository.get_approval(approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found."
        )
    if approval.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval request has already been approved.",
        )

    proposed = tools.create_change_request_mock(
        approval.request.title,
        approval.request.description,
        approval.request.risk_level,
    )
    approved_result = MockChangeRequest.model_validate(
        {**proposed.model_dump(mode="json"), "status": "approved"}
    )
    repository.mark_approved(approval_id, approved_result)
    tool_call = ToolCallRecord(
        tool_name="create_change_request_mock",
        arguments=approval.request.model_dump(mode="json"),
        status="completed",
        result=approved_result.model_dump(mode="json"),
        requires_human_approval=True,
    )
    return ApprovalResponse(
        approval_id=approval.approval_id,
        session_id=approval.session_id,
        final_answer=(
            "Human approval recorded. The approved mock change-request action "
            "has been returned without creating an external record."
        ),
        tool_calls=[tool_call],
        approved_mock_action=approved_result,
    )
