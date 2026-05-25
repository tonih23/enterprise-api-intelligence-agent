"""Request and response contracts for document retrieval."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

RetrievalMode = Literal["keyword", "vector", "hybrid"]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SearchFilters(BaseModel):
    """Exact metadata restrictions applied to retrieval candidates."""

    model_config = ConfigDict(extra="forbid")

    domain: NonEmptyText | None = None
    system: NonEmptyText | None = None
    api_name: NonEmptyText | None = None
    data_classification: NonEmptyText | None = None


class SearchRequest(BaseModel):
    """Search input accepted by the RAG retrieval API."""

    query: NonEmptyText
    top_k: int = Field(default=5, ge=1, le=50)
    mode: RetrievalMode = "hybrid"
    filters: SearchFilters | None = None


class RetrievedChunk(BaseModel):
    """An indexed corpus chunk returned as evidence for an answer."""

    chunk_id: str
    text: str
    score: float
    source_path: str
    metadata: dict[str, Any]
    retrieval_mode: RetrievalMode


class SearchResponse(BaseModel):
    """Ranked retrieval response returned to callers."""

    query: str
    mode: RetrievalMode
    results: list[RetrievedChunk]
