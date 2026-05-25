"""Deterministic policy checks for synthetic-only agent operation."""

from __future__ import annotations

import re
from typing import Literal

from app.agent.state import (
    AgentRequest,
    AgentState,
    CreateChangeRequestToolRequest,
    GetApiDetailsToolRequest,
)

MIN_DOCUMENT_SCORE = 0.01
RESTRICTED_DISCLOSURE = re.compile(
    r"\b(?:show|give|provide|reveal|expose|dump|share|send|retrieve|list|"
    r"access|get|obtain|download|export|tell me|what is|what are)"
    r"\b.{0,60}\b(?:secret|secrets|credential|credentials|token|tokens|"
    r"api key|api keys|private data|internal data)\b",
    re.IGNORECASE,
)
REAL_SYSTEM_ACCESS = re.compile(
    r"\b(?:access|connect to|query|call|log into|login to|use)\b.{0,50}"
    r"\b(?:real|production|company|internal|corporate)\b.{0,25}"
    r"\b(?:system|systems|api|database|service|tenant)\b",
    re.IGNORECASE,
)
CHANGE_ACTION = re.compile(
    r"\b(?:create|open|submit|delete|disable|retire|revoke|rotate|modify|"
    r"update|deploy)\b.{0,70}\b(?:change request|api|endpoint|lifecycle|"
    r"subscription|credential|token|tool)\b",
    re.IGNORECASE,
)
SENSITIVE_TOOL_NAMES = {"create_change_request_mock"}
FACTUAL_READ_TOOLS = {"get_api_details", "search_api_catalog"}


def _request_text(request: AgentRequest) -> str:
    parts = [request.query]
    if request.requested_tool is not None:
        parts.append(str(request.requested_tool.arguments.model_dump(mode="json")))
    return " ".join(parts)


def restricted_reason(request: AgentRequest) -> str | None:
    """Return a blocking reason for prohibited information or system access."""

    text = _request_text(request)
    if RESTRICTED_DISCLOSURE.search(text):
        return "requests for secrets, credentials, tokens, or private data are blocked"
    if REAL_SYSTEM_ACCESS.search(text):
        return "requests to access real company systems are blocked"
    return None


def action_requires_approval(request: AgentRequest) -> bool:
    """Return whether a requested change must stop at human approval."""

    if isinstance(request.requested_tool, CreateChangeRequestToolRequest):
        return True
    return CHANGE_ACTION.search(request.query) is not None


def sensitive_tool_is_allowed(tool_name: str, *, human_approval_present: bool) -> bool:
    """Permit sensitive mock execution only after an approval decision."""

    return tool_name not in SENSITIVE_TOOL_NAMES or human_approval_present


def request_guardrail_node(state: AgentState) -> dict[str, object]:
    """Block prohibited requests and redirect change actions to approval."""

    reason = restricted_reason(state["request"])
    if reason is not None:
        return {
            "route": "blocked_by_guardrail",
            "guardrail_status": "blocked",
            "guardrail_reason": reason,
            "draft_answer": (
                "I cannot help with that request because this enterprise-style "
                "demo does not access or disclose real company systems, secrets, "
                "credentials, tokens, or private data. It operates only on "
                "synthetic local documentation and mock actions."
            ),
        }
    if action_requires_approval(state["request"]):
        return {
            "route": "require_human_approval",
            "guardrail_status": "approval_required",
            "guardrail_reason": (
                "destructive or change-management actions require human approval"
            ),
        }
    return {"guardrail_status": "passed", "guardrail_reason": None}


def request_guardrail_path(
    state: AgentState,
) -> Literal["route", "approval", "blocked"]:
    """Select the next graph stage after request policy evaluation."""

    if state["guardrail_status"] == "blocked":
        return "blocked"
    if state["guardrail_status"] == "approval_required":
        return "approval"
    return "route"


def tool_guardrail_node(state: AgentState) -> dict[str, object]:
    """Enforce policy immediately before any MCP tool invocation."""

    request = state["request"]
    reason = restricted_reason(request)
    if reason is not None:
        return request_guardrail_node(state)
    if request.requested_tool is not None and not sensitive_tool_is_allowed(
        request.requested_tool.tool_name, human_approval_present=False
    ):
        return {
            "route": "require_human_approval",
            "guardrail_status": "approval_required",
            "guardrail_reason": "sensitive tools require human approval before execution",
        }
    return {"guardrail_status": "passed", "guardrail_reason": None}


def tool_guardrail_path(
    state: AgentState,
) -> Literal["tool", "approval", "blocked"]:
    """Select execution, approval, or refusal after tool policy evaluation."""

    if state["guardrail_status"] == "blocked":
        return "blocked"
    if state["guardrail_status"] == "approval_required":
        return "approval"
    return "tool"


def final_guardrail_node(state: AgentState) -> dict[str, object]:
    """Require supported synthetic evidence before formatting factual output."""

    if state["guardrail_status"] == "blocked":
        return {}
    if state["route"] == "answer_with_rag":
        if (
            not state["sources"]
            or not state["retrieved_chunks"]
            or max(chunk.score for chunk in state["retrieved_chunks"])
            < MIN_DOCUMENT_SCORE
        ):
            return _clarification(
                "I could not retrieve sufficiently strong evidence from the "
                "synthetic demo documentation. Please specify the documented API, "
                "endpoint, or runbook topic you want to investigate."
            )
    if state["route"] == "call_mcp_tool":
        completed_tool_names = {
            call.tool_name for call in state["tool_calls"] if call.status == "completed"
        }
        if completed_tool_names & FACTUAL_READ_TOOLS and not state["sources"]:
            return _clarification(
                "I could not find a sourced match in the synthetic demo catalogue. "
                "Please specify a documented fictional API or topic."
            )
        if isinstance(
            state["request"].requested_tool, GetApiDetailsToolRequest
        ) and any(call.status == "failed" for call in state["tool_calls"]):
            return _clarification(
                "I cannot confirm that API name in the synthetic demo "
                "specifications. Please name a documented fictional API."
            )
    return {"guardrail_status": "passed", "guardrail_reason": None}


def _clarification(message: str) -> dict[str, object]:
    return {
        "route": "ask_clarification",
        "guardrail_status": "clarification_required",
        "guardrail_reason": "insufficient sourced evidence for a factual answer",
        "clarification_prompt": message,
        "draft_answer": None,
    }
