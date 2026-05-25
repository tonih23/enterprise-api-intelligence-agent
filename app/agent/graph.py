"""Compiled LangGraph workflow for deterministic local agent execution."""

from typing import Protocol

from langgraph.graph import END, START, StateGraph

from app.agent.guardrails import (
    final_guardrail_node,
    request_guardrail_node,
    request_guardrail_path,
    tool_guardrail_node,
    tool_guardrail_path,
)
from app.agent.nodes.final_answer import create_final_answer_node
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
from app.llm.provider import AnswerSynthesizer, create_answer_synthesizer
from app.mcp_server.tools import CatalogRetriever, McpToolService
from app.observability.phoenix import (
    AgentTracer,
    NoOpTracer,
    get_agent_tracer,
    traced_node,
)


class CompiledAgentGraph(Protocol):
    """Small invocation interface exposed by the compiled graph."""

    def invoke(self, input: AgentState) -> AgentState:
        """Execute the workflow to completion."""


def build_agent_graph(
    *,
    retriever: CatalogRetriever,
    mcp_tools: LocalMcpTools | None = None,
    router_backend: RouterBackend = "deterministic",
    tracer: AgentTracer | None = None,
    answer_synthesizer: AnswerSynthesizer | None = None,
) -> CompiledAgentGraph:
    """Compile the deterministic graph with injected retrieval and tool services."""

    tools = mcp_tools or McpToolService(retriever=retriever)
    configured_tracer = tracer or NoOpTracer()
    configured_synthesizer = answer_synthesizer or AnswerSynthesizer()
    graph = StateGraph(AgentState)
    graph.add_node(
        "request_guardrails",
        traced_node("request_guardrails", request_guardrail_node, configured_tracer),
    )
    graph.add_node(
        "router",
        traced_node("router", create_router(router_backend), configured_tracer),
    )
    graph.add_node(
        "rag", traced_node("rag", create_rag_node(retriever), configured_tracer)
    )
    graph.add_node("mcp", traced_node("mcp", create_mcp_node(tools), configured_tracer))
    graph.add_node(
        "tool_guardrails",
        traced_node("tool_guardrails", tool_guardrail_node, configured_tracer),
    )
    graph.add_node(
        "human_approval",
        traced_node("human_approval", human_approval_node, configured_tracer),
    )
    graph.add_node(
        "final_guardrails",
        traced_node("final_guardrails", final_guardrail_node, configured_tracer),
    )
    graph.add_node(
        "final_answer",
        traced_node(
            "final_answer",
            create_final_answer_node(configured_synthesizer, configured_tracer),
            configured_tracer,
        ),
    )

    graph.add_edge(START, "request_guardrails")
    graph.add_conditional_edges(
        "request_guardrails",
        request_guardrail_path,
        {
            "route": "router",
            "approval": "human_approval",
            "blocked": "final_guardrails",
        },
    )
    graph.add_conditional_edges(
        "router",
        select_route,
        {
            "answer_with_rag": "rag",
            "call_mcp_tool": "tool_guardrails",
            "require_human_approval": "human_approval",
            "ask_clarification": "final_guardrails",
        },
    )
    graph.add_conditional_edges(
        "tool_guardrails",
        tool_guardrail_path,
        {
            "tool": "mcp",
            "approval": "human_approval",
            "blocked": "final_guardrails",
        },
    )
    graph.add_edge("rag", "final_guardrails")
    graph.add_edge("mcp", "final_guardrails")
    graph.add_edge("human_approval", "final_guardrails")
    graph.add_edge("final_guardrails", "final_answer")
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
        tracer: AgentTracer | None = None,
        answer_synthesizer: AnswerSynthesizer | None = None,
    ) -> None:
        self.tracer = tracer or NoOpTracer()
        self.router_backend = router_backend
        self.graph = build_agent_graph(
            retriever=retriever,
            mcp_tools=mcp_tools,
            router_backend=router_backend,
            tracer=self.tracer,
            answer_synthesizer=answer_synthesizer,
        )

    def invoke(self, request: AgentRequest) -> AgentResponse:
        """Execute one request and return a stable typed response."""

        with self.tracer.span(
            "agent.run",
            {
                "data_scope": "synthetic_demo",
                "router_backend": self.router_backend,
                "retrieval_mode": request.mode,
                "top_k": request.top_k,
            },
        ) as span:
            completed_state = self.graph.invoke(initial_state(request))
            response = response_from_state(completed_state)
            span.set_attribute("route_taken", response.route_taken)
            span.set_attribute("number_of_sources", len(response.sources))
            span.set_attribute("tool_call_count", len(response.tool_calls))
            span.set_attribute("approval_status", response.approval_status)
            span.set_attribute("llm_provider", response.answer_synthesis.provider)
            span.set_attribute("answer_synthesis_mode", response.answer_synthesis.mode)
            if response.answer_synthesis.model:
                span.set_attribute("llm_model", response.answer_synthesis.model)
            return response


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
        tracer=get_agent_tracer(configured_settings),
        answer_synthesizer=create_answer_synthesizer(configured_settings),
    )
