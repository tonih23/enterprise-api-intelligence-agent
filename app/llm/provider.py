"""Small provider boundary for optional final-answer synthesis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.llm.schemas import AnswerSynthesisStatus, SynthesizedAnswer

if TYPE_CHECKING:
    from app.config import Settings


class LlmProviderError(RuntimeError):
    """Expected LLM provider failure handled through deterministic fallback."""


class TextGenerationProvider(Protocol):
    """Minimal interface needed by the final-answer node."""

    model_name: str

    def generate(self, prompt: str) -> str:
        """Generate grounded final-answer text."""


class AnswerSynthesizer:
    """Produce optional LLM answers with a deterministic fallback."""

    def __init__(
        self,
        provider: TextGenerationProvider | None = None,
        *,
        configured_model: str | None = None,
        setup_warning: str | None = None,
    ) -> None:
        self.provider = provider
        self.configured_model = configured_model
        self.setup_warning = setup_warning

    def synthesize(
        self, *, prompt: str, deterministic_answer: str
    ) -> SynthesizedAnswer:
        """Use the configured provider, falling back cleanly when unavailable."""
        if self.provider is None:
            return SynthesizedAnswer(
                answer_text=deterministic_answer,
                status=AnswerSynthesisStatus(
                    model=self.configured_model,
                    warning=self.setup_warning,
                ),
            )

        try:
            generated_text = self.provider.generate(prompt).strip()
            if not generated_text:
                raise LlmProviderError(
                    "Gemini returned no answer text; using deterministic answer synthesis."
                )
        except LlmProviderError as error:
            return SynthesizedAnswer(
                answer_text=deterministic_answer,
                status=AnswerSynthesisStatus(
                    model=self.provider.model_name,
                    warning=str(error),
                ),
            )

        return SynthesizedAnswer(
            answer_text=generated_text,
            status=AnswerSynthesisStatus(
                mode="gemini",
                model=self.provider.model_name,
            ),
        )


def create_answer_synthesizer(settings: Settings) -> AnswerSynthesizer:
    """Configure the requested provider without requiring an LLM by default."""
    if settings.llm_provider == "none":
        return AnswerSynthesizer()

    from app.llm.gemini import GeminiProvider

    try:
        provider = GeminiProvider.from_environment(settings.llm_model)
    except LlmProviderError as error:
        return AnswerSynthesizer(
            configured_model=settings.llm_model,
            setup_warning=str(error),
        )
    return AnswerSynthesizer(provider)
