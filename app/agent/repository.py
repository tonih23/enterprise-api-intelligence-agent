"""Persistence boundary for local conversations and approval records."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agent.state import AgentResponse
from app.mcp_server.schemas import ChangeRequestInput, MockChangeRequest

ApprovalRecordStatus = Literal["pending_human_approval", "approved"]


class SessionTurn(BaseModel):
    """One locally recorded user interaction and graph response."""

    turn_id: str
    session_id: str
    user_message: str
    response: AgentResponse
    approval_id: str | None = None
    created_at: datetime


class ApprovalRecord(BaseModel):
    """Pending or approved execution record for a mock governed action."""

    approval_id: str
    session_id: str
    request: ChangeRequestInput
    status: ApprovalRecordStatus = "pending_human_approval"
    result: MockChangeRequest | None = None
    created_at: datetime
    decided_at: datetime | None = None


class SessionRecord(BaseModel):
    """History held for one conversation session."""

    session_id: str
    turns: list[SessionTurn] = Field(default_factory=list)
    approvals: list[ApprovalRecord] = Field(default_factory=list)


class AgentRepository(Protocol):
    """Storage operations used by the HTTP agent surface."""

    def add_turn(
        self,
        *,
        session_id: str,
        user_message: str,
        response: AgentResponse,
        approval_id: str | None = None,
    ) -> SessionTurn:
        """Store one completed graph interaction."""

    def create_approval(
        self, *, session_id: str, request: ChangeRequestInput
    ) -> ApprovalRecord:
        """Store a pending sensitive mock request."""

    def get_approval(self, approval_id: str) -> ApprovalRecord | None:
        """Look up one approval request."""

    def mark_approved(
        self, approval_id: str, result: MockChangeRequest
    ) -> ApprovalRecord:
        """Record completion of an approved mock action."""

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Return basic recorded history for a session."""


class InMemoryAgentRepository:
    """Thread-safe local storage suitable for development and API tests."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._approvals: dict[str, ApprovalRecord] = {}
        self._lock = Lock()

    def add_turn(
        self,
        *,
        session_id: str,
        user_message: str,
        response: AgentResponse,
        approval_id: str | None = None,
    ) -> SessionTurn:
        turn = SessionTurn(
            turn_id=f"turn_{uuid4().hex}",
            session_id=session_id,
            user_message=user_message,
            response=response,
            approval_id=approval_id,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            session = self._sessions.setdefault(
                session_id, SessionRecord(session_id=session_id)
            )
            session.turns.append(turn)
        return turn

    def create_approval(
        self, *, session_id: str, request: ChangeRequestInput
    ) -> ApprovalRecord:
        approval = ApprovalRecord(
            approval_id=f"approval_{uuid4().hex}",
            session_id=session_id,
            request=request,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            session = self._sessions.setdefault(
                session_id, SessionRecord(session_id=session_id)
            )
            session.approvals.append(approval)
            self._approvals[approval.approval_id] = approval
        return approval

    def get_approval(self, approval_id: str) -> ApprovalRecord | None:
        with self._lock:
            return self._approvals.get(approval_id)

    def mark_approved(
        self, approval_id: str, result: MockChangeRequest
    ) -> ApprovalRecord:
        with self._lock:
            approval = self._approvals[approval_id]
            approval.status = "approved"
            approval.result = result
            approval.decided_at = datetime.now(UTC)
            return approval

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            return self._sessions.get(session_id)


_repository = InMemoryAgentRepository()


def get_agent_repository() -> AgentRepository:
    """Return local storage until a configured Postgres adapter is introduced."""

    return _repository
