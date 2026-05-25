"""Final response generation from accumulated, guarded evidence."""

import json
from collections.abc import Callable

from app.agent.state import AgentState
from app.llm.provider import AnswerSynthesizer


def deterministic_answer(state: AgentState) -> str:
    """Produce the stable no-provider answer used by default and on fallback."""

    if state["draft_answer"] is not None:
        return state["draft_answer"]
    if state["route"] == "ask_clarification":
        return (
            state["clarification_prompt"]
            or "Please provide more detail about the API question."
        )
    if not state["retrieved_chunks"]:
        return (
            "No matching synthetic documentation evidence was retrieved for "
            "this question."
        )

    evidence = "\n".join(
        f"- {chunk.text.strip()} (source: {chunk.source_path})"
        for chunk in state["retrieved_chunks"]
    )
    return (
        "Based only on the synthetic documentation corpus for this demo, "
        "retrieved relevant evidence:\n"
        f"{evidence}"
    )


def synthesis_prompt(state: AgentState, fallback_answer: str) -> str:
    """Build a bounded prompt using only guarded synthetic evidence."""

    chunks = [
        {
            "text": chunk.text[:2000],
            "source_path": chunk.source_path,
            "metadata": chunk.metadata,
        }
        for chunk in state["retrieved_chunks"][:5]
    ]
    tools = [tool_call.model_dump(mode="json") for tool_call in state["tool_calls"]]
    return (
        "You are generating the final response for an enterprise-style portfolio demo.\n"
        "Rules:\n"
        "- Answer only from the retrieved chunks or tool results below.\n"
        "- Do not invent API names, operations, facts, or approval outcomes.\n"
        "- Do not claim access to real company systems or private enterprise data.\n"
        "- When discussing documentation or tool results, state that the data is "
        "synthetic/demo data.\n"
        "- Keep the answer concise: no more than four sentences.\n"
        "- If approval is pending, explain that no risky mock action has executed.\n"
        "- If clarification is required, ask one concise clarification question.\n\n"
        f"Route: {state['route']}\n"
        f"User question: {state['request'].query}\n"
        f"Deterministic control answer: {fallback_answer}\n"
        f"Retrieved chunks: {json.dumps(chunks)}\n"
        f"Tool calls: {json.dumps(tools)}\n"
    )


def create_final_answer_node(
    synthesizer: AnswerSynthesizer | None = None,
) -> Callable[[AgentState], dict[str, object]]:
    """Create a final-answer node with optional synthesis injection for testing."""

    configured_synthesizer = synthesizer or AnswerSynthesizer()

    def final_answer_node(state: AgentState) -> dict[str, object]:
        fallback_answer = deterministic_answer(state)

        # Keep policy refusal text local and deterministic.
        if state["route"] == "blocked_by_guardrail":
            result = AnswerSynthesizer().synthesize(
                prompt="",
                deterministic_answer=fallback_answer,
            )
        else:
            result = configured_synthesizer.synthesize(
                prompt=synthesis_prompt(state, fallback_answer),
                deterministic_answer=fallback_answer,
            )
        return {
            "answer_text": result.answer_text,
            "answer_synthesis": result.status,
        }

    return final_answer_node


final_answer_node = create_final_answer_node()
