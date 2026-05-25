"""Deterministic request router with an interchangeable node boundary."""

from collections.abc import Callable

from app.agent.state import AgentRoute, AgentState
from app.config import RouterBackend

RouterNode = Callable[[AgentState], dict[str, object]]
UNCLEAR_REQUESTS = {
    "api",
    "do it",
    "help",
    "search",
    "tell me more",
}


def deterministic_router(state: AgentState) -> dict[str, object]:
    """Choose a branch using transparent rules rather than an LLM call."""

    request = state["request"]
    if request.requested_tool is not None:
        return {"route": "call_mcp_tool"}

    normalized_query = " ".join(request.query.lower().split())
    if normalized_query in UNCLEAR_REQUESTS:
        return {
            "route": "ask_clarification",
            "clarification_prompt": (
                "Please specify an API, endpoint, document topic, or local tool "
                "action to investigate."
            ),
        }
    return {"route": "answer_with_rag"}


def select_route(state: AgentState) -> AgentRoute:
    """Return the branch set by the router node."""

    route = state["route"]
    if route is None:
        raise ValueError("Router did not select an agent route")
    return route


def create_router(backend: RouterBackend = "deterministic") -> RouterNode:
    """Select a router implementation through configuration."""

    if backend == "deterministic":
        return deterministic_router
    raise ValueError(f"Unsupported agent router backend: {backend}")
