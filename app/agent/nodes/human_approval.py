"""Approval gate for sensitive proposed actions."""

from app.agent.state import AgentState, CreateChangeRequestToolRequest, ToolCallRecord


def human_approval_node(state: AgentState) -> dict[str, object]:
    """Record a pending action without invoking the sensitive MCP tool."""

    request = state["request"]
    tool_request = request.requested_tool
    if isinstance(tool_request, CreateChangeRequestToolRequest):
        arguments = tool_request.arguments.model_dump(mode="json")
    else:
        arguments = {
            "title": "Proposed synthetic API change request",
            "description": request.query,
            "risk_level": "medium",
        }

    pending_call = ToolCallRecord(
        tool_name="create_change_request_mock",
        arguments=arguments,
        status="blocked_pending_approval",
        requires_human_approval=True,
    )
    return {
        "tool_calls": [pending_call],
        "approval_status": "pending_human_approval",
        "draft_answer": (
            "Human approval is required before the mock change-request tool can "
            "be invoked. No action has been executed."
        ),
    }
