"""Tests for lightweight Streamlit demo helper behavior."""

from urllib.error import URLError

import pytest

from demo.streamlit_app import DemoApiError, flow_steps, post_json


def test_flow_steps_includes_approval_only_for_pending_action() -> None:
    steps = flow_steps({"route_taken": "require_human_approval"})

    assert ("Human approval", "pending") in steps
    assert ("Retrieval", "complete") not in steps
    assert steps[-1] == ("Final answer", "complete")


def test_post_json_explains_when_fastapi_backend_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unreachable(*args, **kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr("demo.streamlit_app.urlopen", unreachable)

    with pytest.raises(DemoApiError, match="FastAPI backend is not reachable"):
        post_json(
            "http://127.0.0.1:8000",
            "/agent/chat",
            {"user_message": "Synthetic question"},
        )
