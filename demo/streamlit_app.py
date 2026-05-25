"""Streamlit client for demonstrating the local FastAPI agent."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

DEFAULT_API_URL = os.getenv("API_AGENT_DEMO_API_URL", "http://127.0.0.1:8000")
HTTP_TIMEOUT_SECONDS = 20


class DemoApiError(RuntimeError):
    """Presentable error from the local FastAPI demo backend."""


def post_json(api_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to the local API without duplicating agent behavior."""

    url = f"{api_url.rstrip('/')}{path}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8")).get("detail")
        except (json.JSONDecodeError, AttributeError):
            detail = None
        message = detail or "The backend rejected the request."
        raise DemoApiError(f"FastAPI returned HTTP {error.code}: {message}") from error
    except (TimeoutError, URLError) as error:
        raise DemoApiError(
            "The FastAPI backend is not reachable. Start it locally and confirm "
            f"the configured URL: {api_url}"
        ) from error


def flow_steps(response: dict[str, Any]) -> list[tuple[str, str]]:
    """Build a concise workflow visualization from the API result."""

    route = response.get("route_taken")
    steps = [("Input", "complete"), ("Guardrails", "complete")]
    if route == "blocked_by_guardrail":
        return steps[:-1] + [("Guardrails", "blocked"), ("Final answer", "complete")]

    steps.append(("Router", "complete"))
    if route == "answer_with_rag":
        steps.append(("Retrieval", "complete"))
    elif route == "call_mcp_tool":
        steps.append(("MCP tool", "complete"))
    elif route == "require_human_approval":
        steps.append(("Human approval", "pending"))
    else:
        steps.append(("Clarification", "requested"))
    steps.append(("Final answer", "complete"))
    return steps


def synthesis_display(response: dict[str, Any]) -> tuple[str, str, str | None]:
    """Return display-ready synthesis metadata."""

    synthesis = response.get("answer_synthesis") or {}
    mode = "Gemini" if synthesis.get("mode") == "gemini" else "Deterministic"
    model = synthesis.get("model") or "Not configured"
    return mode, model, synthesis.get("warning")


def render_flow(response: dict[str, Any]) -> None:
    """Render the route as a simple visual timeline."""

    st.subheader("Agent Flow")
    steps = flow_steps(response)
    columns = st.columns(len(steps))
    for number, ((label, outcome), column) in enumerate(
        zip(steps, columns, strict=True), start=1
    ):
        with column:
            st.markdown(f"**{number}. {label}**")
            st.code(outcome)


def render_result(api_url: str, response: dict[str, Any]) -> None:
    """Show the structured response returned by FastAPI."""

    render_flow(response)
    st.subheader("Final Answer")
    st.write(response.get("final_answer", "No answer returned."))

    answer_mode, llm_model, synthesis_warning = synthesis_display(response)
    summary_columns = st.columns(4)
    summary_columns[0].metric("Route Taken", response.get("route_taken", "-"))
    summary_columns[1].metric("Approval Status", response.get("approval_status", "-"))
    summary_columns[2].metric("Answer Synthesis", answer_mode)
    summary_columns[3].metric("LLM Model", llm_model)
    st.caption(f"Session: `{response.get('session_id', '-')}`")
    if synthesis_warning:
        st.warning(synthesis_warning)

    if response.get("approval_status") == "pending_human_approval" and response.get(
        "approval_id"
    ):
        st.warning(
            "A mock action is waiting for human approval. No external action "
            "has been executed."
        )
        if st.button("Approve mock action", type="secondary"):
            try:
                approved = post_json(
                    api_url, f"/agent/approve/{response['approval_id']}", {}
                )
            except DemoApiError as error:
                st.error(str(error))
            else:
                st.success(approved["final_answer"])
                st.json(approved)

    st.subheader("Tool Calls")
    tool_calls = response.get("tool_calls", [])
    if tool_calls:
        for tool_call in tool_calls:
            with st.expander(
                f"{tool_call['tool_name']} - {tool_call['status']}", expanded=True
            ):
                st.json(tool_call)
    else:
        st.caption("No local tool was called for this request.")

    st.subheader("Sources")
    sources = response.get("sources", [])
    if sources:
        st.dataframe(sources, width="stretch", hide_index=True)
    else:
        st.caption("No documentation source was returned.")

    st.subheader("Retrieved Chunks / Evidence")
    evidence = response.get("retrieved_chunks", [])
    if evidence:
        for chunk in evidence:
            title = f"{chunk['source_path']} | score {chunk['score']:.4f}"
            with st.expander(title, expanded=False):
                st.write(chunk["text"])
                st.json(chunk.get("metadata", {}))
    else:
        st.caption("No retrieved text evidence was returned for this route.")


def main() -> None:
    """Run the local portfolio demonstration UI."""

    st.set_page_config(
        page_title="Enterprise API Intelligence Agent Demo",
        layout="wide",
    )
    st.title("Enterprise API Intelligence Agent")
    st.caption(
        "Local portfolio demo over synthetic API documentation and mock actions only."
    )

    with st.sidebar:
        st.header("Demo Settings")
        api_url = st.text_input("FastAPI backend URL", value=DEFAULT_API_URL)
        retrieval_mode = st.selectbox(
            "Retrieval mode",
            options=["keyword", "vector", "hybrid"],
            index=2,
            help="Applied to documentation questions handled through RAG.",
        )
        top_k = st.slider("Top results", min_value=1, max_value=10, value=5)
        backend_guidance = st.radio(
            "Embedding backend guidance",
            options=[
                "local_hashing fallback",
                "BGE large local semantic embeddings",
            ],
            help="Guidance only. The FastAPI backend and index control embeddings.",
        )
        if backend_guidance == "local_hashing fallback":
            st.info(
                "`local_hashing` is deterministic and offline, but not semantic. "
                "It is suitable for local smoke tests."
            )
        else:
            st.info(
                "Set the backend to `sentence_transformers` with "
                "`BAAI/bge-large-en-v1.5` or a local model folder, then ingest "
                "into a fresh 1024-dimensional index."
            )

    with st.form("agent_question"):
        question = st.text_area(
            "Question",
            placeholder="Which action requires human approval?",
            height=90,
        )
        submitted = st.form_submit_button("Ask Agent", type="primary")

    if submitted:
        if not question.strip():
            st.warning("Enter a question before submitting.")
        else:
            request_payload: dict[str, Any] = {
                "user_message": question,
                "mode": retrieval_mode,
                "top_k": top_k,
            }
            if st.session_state.get("session_id"):
                request_payload["session_id"] = st.session_state.session_id
            try:
                with st.spinner("Calling local FastAPI agent..."):
                    response = post_json(api_url, "/agent/chat", request_payload)
            except DemoApiError as error:
                st.error(str(error))
            else:
                st.session_state.response = response
                st.session_state.session_id = response.get("session_id")

    if st.session_state.get("response"):
        render_result(api_url, st.session_state.response)


if __name__ == "__main__":
    main()
