"""Google Gemini implementation for optional answer synthesis."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.provider import LlmProviderError


class _GeminiCredentials(BaseSettings):
    """Load the Gemini secret only after the optional provider is selected."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="GOOGLE_API_KEY",
    )


class GeminiProvider:
    """Generate final-answer text using the official Google GenAI SDK."""

    def __init__(self, *, model_name: str, api_key: str) -> None:
        self.model_name = model_name
        self._api_key = api_key

    @classmethod
    def from_environment(cls, model_name: str) -> GeminiProvider:
        """Read credentials only when Gemini has been explicitly selected."""
        configured_key = _GeminiCredentials().google_api_key
        api_key = configured_key.get_secret_value() if configured_key else None
        if not api_key:
            raise LlmProviderError(
                "Gemini synthesis is configured but GOOGLE_API_KEY is not set; "
                "using deterministic answer synthesis."
            )
        return cls(model_name=model_name, api_key=api_key)

    def generate(self, prompt: str) -> str:
        """Call Gemini for final-answer synthesis only."""
        try:
            from google import genai

            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            text = response.text
        except Exception as error:
            raise LlmProviderError(
                "Gemini answer synthesis is unavailable; "
                "using deterministic answer synthesis."
            ) from error

        if not text or not text.strip():
            raise LlmProviderError(
                "Gemini returned no answer text; using deterministic answer synthesis."
            )
        return text.strip()
