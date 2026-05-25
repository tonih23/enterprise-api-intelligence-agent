"""Retrieval node for documentation-grounded questions."""

from collections.abc import Callable

from app.agent.state import AgentState, SourceReference
from app.mcp_server.tools import CatalogRetriever
from app.rag.schemas import SearchRequest


def create_rag_node(
    retriever: CatalogRetriever,
) -> Callable[[AgentState], dict[str, object]]:
    """Build a node that executes configured document retrieval."""

    def retrieve_documents(state: AgentState) -> dict[str, object]:
        request = state["request"]
        chunks = retriever.search(
            SearchRequest(
                query=request.query,
                top_k=request.top_k,
                mode=request.mode,
                filters=request.filters,
            )
        )
        sources = [
            SourceReference(
                source_path=chunk.source_path,
                chunk_id=chunk.chunk_id,
                score=chunk.score,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]
        return {"retrieved_chunks": chunks, "sources": sources}

    return retrieve_documents
