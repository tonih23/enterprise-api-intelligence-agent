"""Tests for selectable ingestion embedding implementations."""

import math

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.rag.embeddings import (
    LOCAL_HASHING_DIMENSION,
    LocalHashingEmbedder,
    SentenceTransformerEmbedder,
    create_embedder,
)


def test_settings_select_embedding_backend_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_AGENT_EMBEDDING_BACKEND", "local_hashing")

    settings = Settings(_env_file=None)

    assert settings.embedding_backend == "local_hashing"
    assert isinstance(
        create_embedder(
            settings.embedding_backend,
            model_name=settings.embedding_model_name,
            batch_size=settings.embedding_batch_size,
        ),
        LocalHashingEmbedder,
    )


def test_sentence_transformer_backend_selection_is_lazy() -> None:
    embedder = create_embedder(
        "sentence_transformers",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=8,
    )

    assert isinstance(embedder, SentenceTransformerEmbedder)
    assert embedder._model is None


def test_settings_reject_unsupported_embedding_backend() -> None:
    with pytest.raises(ValidationError):
        Settings(embedding_backend="unsupported")  # type: ignore[arg-type]


def test_local_hashing_vectors_have_fixed_dimension() -> None:
    embedder = LocalHashingEmbedder()

    vector = embedder.embed_texts(["Search synthetic trials"])[0]

    assert embedder.dimension == LOCAL_HASHING_DIMENSION
    assert len(vector) == LOCAL_HASHING_DIMENSION


def test_local_hashing_vectors_are_deterministic() -> None:
    text = "GET /trials/TRIAL-SYN-204/sites"

    first = LocalHashingEmbedder().embed_texts([text])[0]
    second = LocalHashingEmbedder().embed_texts([text])[0]

    assert first == second


@pytest.mark.parametrize("text", ["hcp search cardiology", "", "approval required"])
def test_local_hashing_vectors_are_normalized(text: str) -> None:
    vector = LocalHashingEmbedder().embed_texts([text])[0]
    magnitude = math.sqrt(sum(value * value for value in vector))

    assert magnitude == pytest.approx(1.0)
