"""Deterministic final response generation from accumulated evidence."""

from app.agent.state import AgentState


def final_answer_node(state: AgentState) -> dict[str, object]:
    """Produce answer text without invoking an external language model."""

    if state["draft_answer"] is not None:
        return {"answer_text": state["draft_answer"]}
    if state["route"] == "ask_clarification":
        return {
            "answer_text": state["clarification_prompt"]
            or "Please provide more detail about the API question."
        }
    if not state["retrieved_chunks"]:
        return {
            "answer_text": (
                "No matching synthetic documentation evidence was retrieved for "
                "this question."
            )
        }

    evidence = "\n".join(
        f"- {chunk.text.strip()} (source: {chunk.source_path})"
        for chunk in state["retrieved_chunks"]
    )
    return {
        "answer_text": (
            "Based only on the synthetic documentation corpus for this demo, "
            "retrieved "
            "relevant evidence:\n"
            f"{evidence}"
        )
    }
