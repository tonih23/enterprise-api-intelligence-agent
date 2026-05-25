"""Schemas describing optional LLM answer synthesis."""

from typing import Literal

from pydantic import BaseModel

AnswerSynthesisMode = Literal["deterministic", "gemini"]


class AnswerSynthesisStatus(BaseModel):
    """How the final answer text was produced."""

    mode: AnswerSynthesisMode = "deterministic"
    model: str | None = None
    warning: str | None = None


class SynthesizedAnswer(BaseModel):
    """Answer text and non-sensitive synthesis metadata."""

    answer_text: str
    status: AnswerSynthesisStatus
