"""Tests for selectable ingestion embedding implementations."""

import math
import sys
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.rag.embeddings import (
    LOCAL_HASHING_DIMENSION,
    LocalHashingEmbedder,
    SentenceTransformerEmbedder,
    create_embedder,
)


def test_default_real_embedding_model_is_bge_large() -> None:
    settings = Settings(_env_file=None)

    assert settings.embedding_backend == "local_hashing"
    assert settings.embedding_model_name == "BAAI/bge-large-en-v1.5"


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
        model_name="BAAI/bge-large-en-v1.5",
        batch_size=8,
    )

    assert isinstance(embedder, SentenceTransformerEmbedder)
    assert embedder.model_name == "BAAI/bge-large-en-v1.5"
    assert embedder.local_files_only is False
    assert embedder._model is None


def test_sentence_transformer_loads_configured_local_path_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_model = tmp_path / "bge-large-en-v1.5"
    local_model.mkdir()
    loaded: dict[str, object] = {}
    fake_module = ModuleType("sentence_transformers")

    class FakeSentenceTransformer:
        def __init__(self, model_name: str, *, local_files_only: bool) -> None:
            loaded["model_name"] = model_name
            loaded["local_files_only"] = local_files_only

        def get_sentence_embedding_dimension(self) -> int:
            return 1024

    fake_module.SentenceTransformer = FakeSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setenv("API_AGENT_EMBEDDING_BACKEND", "sentence_transformers")
    monkeypatch.setenv("API_AGENT_EMBEDDING_MODEL_NAME", str(local_model))

    settings = Settings(_env_file=None)
    embedder = create_embedder(
        settings.embedding_backend,
        model_name=settings.embedding_model_name,
        batch_size=settings.embedding_batch_size,
    )

    assert embedder.dimension == 1024
    assert loaded == {
        "model_name": str(local_model),
        "local_files_only": True,
    }


def test_sentence_transformer_rejects_missing_explicit_local_path(
    tmp_path: Path,
) -> None:
    missing_model = tmp_path / "missing-model"

    with pytest.raises(ValueError, match="does not exist"):
        create_embedder(
            "sentence_transformers",
            model_name=str(missing_model),
            batch_size=8,
        )


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
