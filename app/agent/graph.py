"""Compiled LangGraph workflow for deterministic local agent execution."""

from typing import Protocol

from langgraph.graph import END, START, StateGraph

from app.agent.nodes.final_answer import final_answer_node
from app.agent.nodes.human_approval import human_approval_node
from app.agent.nodes.mcp_node import LocalMcpTools, create_mcp_node
from app.agent.nodes.rag_node import create_rag_node
from app.agent.nodes.router import create_router, select_route
from app.agent.state import (
    AgentRequest,
    AgentResponse,
    AgentState,
    initial_state,
    response_from_state,
)
from app.config import RouterBackend, Settings, get_settings
from app.mcp_server.tools import CatalogRetriever, McpToolService


class CompiledAgentGraph(Protocol):
    """Small invocation interface exposed by the compiled graph."""

    def invoke(self, input: AgentState) -> AgentState:
        """Execute the workflow to completion."""


def build_agent_graph(
    *,
    retriever: CatalogRetriever,
    mcp_tools: LocalMcpTools | None = None,
    router_backend: RouterBackend = "deterministic",
) -> CompiledAgentGraph:
    """Compile the deterministic graph with injected retrieval and tool services."""

    tools = mcp_tools or McpToolService(retriever=retriever)
    graph = StateGraph(AgentState)
    graph.add_node("router", create_router(router_backend))
    graph.add_node("rag", create_rag_node(retriever))
    graph.add_node("mcp", create_mcp_node(tools))
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("final_answer", final_answer_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        select_route,
        {
            "answer_with_rag": "rag",
            "call_mcp_tool": "mcp",
            "require_human_approval": "human_approval",
            "ask_clarification": "final_answer",
        },
    )
    graph.add_edge("rag", "final_answer")
    graph.add_edge("mcp", "final_answer")
    graph.add_edge("human_approval", "final_answer")
    graph.add_edge("final_answer", END)
    return graph.compile()


class AgentWorkflow:
    """Typed convenience wrapper around a compiled LangGraph workflow."""

    def __init__(
        self,
        *,
        retriever: CatalogRetriever,
        mcp_tools: LocalMcpTools | None = None,
        router_backend: RouterBackend = "deterministic",
    ) -> None:
        self.graph = build_agent_graph(
            retriever=retriever,
            mcp_tools=mcp_tools,
            router_backend=router_backend,
        )

    def invoke(self, request: AgentRequest) -> AgentResponse:
        """Execute one request and return a stable typed response."""

        completed_state = self.graph.invoke(initial_state(request))
        return response_from_state(completed_state)


def create_agent_workflow(
    *,
    retriever: CatalogRetriever,
    mcp_tools: LocalMcpTools | None = None,
    settings: Settings | None = None,
) -> AgentWorkflow:
    """Construct a workflow using the configured router implementation."""

    configured_settings = settings or get_settings()
    return AgentWorkflow(
        retriever=retriever,
        mcp_tools=mcp_tools,
        router_backend=configured_settings.router_backend,
    )
