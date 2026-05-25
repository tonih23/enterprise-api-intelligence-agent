"""Selectable embedding backends for corpus ingestion."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Protocol

from app.config import EmbeddingBackend

LOCAL_HASHING_DIMENSION = 384
_TOKEN_PATTERN = re.compile(r"[a-z0-9_./{}:-]+")


class Embedder(Protocol):
    """Common interface for vector-generating ingestion backends."""

    @property
    def dimension(self) -> int:
        """Return the fixed vector size."""

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Create one normalized vector for each input text."""


class SentenceTransformerEmbedder:
    """Create semantic vectors with a lazily loaded sentence-transformers model."""

    def __init__(self, model_name: str, *, batch_size: int = 32) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: object | None = None

    def _get_model(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        """Return the embedding vector size declared by the configured model."""

        model = self._get_model()
        dimension = model.get_sentence_embedding_dimension()  # type: ignore[attr-defined]
        if dimension is None:
            raise ValueError(f"Embedding model {self.model_name!r} has no dimension")
        return int(dimension)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed text and normalize vectors for cosine-similarity retrieval."""

        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(  # type: ignore[attr-defined]
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > self.batch_size,
        )
        return vectors.tolist()


class LocalHashingEmbedder:
    """Create deterministic local smoke-test vectors without model downloads."""

    def __init__(self, dimension: int = LOCAL_HASHING_DIMENSION) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Return the configured feature-hash vector size."""

        return self._dimension

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Create normalized lexical feature-hash vectors for local testing."""

        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        tokens = _TOKEN_PATTERN.findall(text.casefold())
        features = tokens + [
            f"{left}::{right}" for left, right in zip(tokens, tokens[1:], strict=False)
        ]
        if not features:
            features = ["<empty>"]

        vector = [0.0] * self.dimension
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:8], byteorder="big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[bucket] += sign

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            vector[0] = 1.0
            return vector
        return [value / magnitude for value in vector]


def create_embedder(
    backend: EmbeddingBackend,
    *,
    model_name: str,
    batch_size: int,
) -> Embedder:
    """Create the configured embedding implementation without eager downloads."""

    if backend == "sentence_transformers":
        return SentenceTransformerEmbedder(model_name, batch_size=batch_size)
    if backend == "local_hashing":
        return LocalHashingEmbedder()
    raise ValueError(f"Unsupported embedding backend: {backend}")
