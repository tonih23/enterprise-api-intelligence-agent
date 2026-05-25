"""Tests for optional final-answer synthesis without external LLM calls."""

import sys
from types import ModuleType, SimpleNamespace

from app.agent.graph import AgentWorkflow, create_agent_workflow
from app.agent.state import AgentRequest
from app.config import Settings
from app.llm.gemini import GeminiProvider
from app.llm.provider import (
    AnswerSynthesizer,
    LlmProviderError,
    create_answer_synthesizer,
)
from app.rag.schemas import RetrievedChunk, SearchRequest


class EvidenceRetriever:
    """Supply sourced synthetic evidence without search dependencies."""

    def search(self, request: SearchRequest) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="hcp-evidence",
                text="The HCP Search API supports searching for HCP candidates.",
                score=0.2,
                source_path="data/api_specs/hcp_search_api.openapi.yaml",
                metadata={"api_name": "hcp_search_api", "synthetic": True},
                retrieval_mode=request.mode,
            )
        ]


class RecordingProvider:
    """Pretend Gemini is available while recording its bounded prompt."""

    model_name = "gemini-2.5-flash"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "In this synthetic demo, the HCP Search API supports candidate search."


class FailingProvider:
    """Represent an unavailable configured Gemini service."""

    model_name = "gemini-2.5-flash"

    def generate(self, prompt: str) -> str:
        raise LlmProviderError(
            "Gemini answer synthesis is unavailable; "
            "using deterministic answer synthesis."
        )


def test_provider_none_does_not_require_google_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    synthesizer = create_answer_synthesizer(
        Settings(_env_file=None, environment="test", llm_provider="none")
    )

    response = AgentWorkflow(
        retriever=EvidenceRetriever(), answer_synthesizer=synthesizer
    ).invoke(AgentRequest(query="Which API finds HCP candidates?"))

    assert response.answer_synthesis.mode == "deterministic"
    assert response.answer_synthesis.provider == "none"
    assert response.answer_synthesis.warning is None
    assert "synthetic documentation corpus" in response.answer_text


def test_mocked_gemini_answer_is_concise_and_evidence_remains_separate() -> None:
    provider = RecordingProvider()

    response = AgentWorkflow(
        retriever=EvidenceRetriever(),
        answer_synthesizer=AnswerSynthesizer(provider),
    ).invoke(AgentRequest(query="Which API finds HCP candidates?"))

    assert response.answer_text.count(".") <= 4
    assert response.answer_synthesis.mode == "gemini"
    assert response.answer_synthesis.provider == "gemini"
    assert response.answer_synthesis.model == "gemini-2.5-flash"
    assert response.sources[0].source_path.endswith("hcp_search_api.openapi.yaml")
    assert response.retrieved_chunks[0].chunk_id == "hcp-evidence"
    assert (
        "Answer only from the retrieved chunks or tool results" in provider.prompts[0]
    )
    assert "Do not invent API names" in provider.prompts[0]


def test_gemini_failure_falls_back_without_crashing() -> None:
    response = AgentWorkflow(
        retriever=EvidenceRetriever(),
        answer_synthesizer=AnswerSynthesizer(FailingProvider()),
    ).invoke(AgentRequest(query="Which API finds HCP candidates?"))

    assert response.answer_synthesis.mode == "deterministic"
    assert response.answer_synthesis.provider == "gemini"
    assert response.answer_synthesis.model == "gemini-2.5-flash"
    assert "unavailable" in (response.answer_synthesis.warning or "")
    assert "synthetic documentation corpus" in response.answer_text


def test_gemini_configuration_without_key_falls_back_before_sdk_call(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "")

    response = create_agent_workflow(
        retriever=EvidenceRetriever(),
        settings=Settings(_env_file=None, environment="test", llm_provider="gemini"),
    ).invoke(AgentRequest(query="Which API finds HCP candidates?"))

    assert response.answer_synthesis.mode == "deterministic"
    assert response.answer_synthesis.model == "gemini-2.5-flash"
    assert "GOOGLE_API_KEY is not set" in (response.answer_synthesis.warning or "")


def test_gemini_provider_uses_mocked_google_genai_client_only_on_generate(
    monkeypatch,
) -> None:
    events: list[tuple[str, str]] = []

    class FakeModels:
        def generate_content(self, *, model: str, contents: str):
            events.append(("model", model))
            events.append(("prompt", contents))
            return SimpleNamespace(text="A grounded synthetic answer.")

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            events.append(("key", api_key))
            self.models = FakeModels()

    fake_google = ModuleType("google")
    fake_genai = ModuleType("google.genai")
    fake_genai.Client = FakeClient  # type: ignore[attr-defined]
    fake_google.genai = fake_genai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setenv("GOOGLE_API_KEY", "demo-key")

    provider = GeminiProvider.from_environment("gemini-2.5-flash")
    assert events == []

    assert provider.generate("bounded prompt") == "A grounded synthetic answer."
    assert events == [
        ("key", "demo-key"),
        ("model", "gemini-2.5-flash"),
        ("prompt", "bounded prompt"),
    ]
