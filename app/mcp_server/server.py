"""FastMCP stdio server exposing local synthetic API intelligence tools."""

from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.mcp_server.schemas import (
    ApiDetails,
    CatalogSearchResult,
    MockChangeRequest,
    OpenAPIValidationResult,
    RiskLevel,
)
from app.mcp_server.tools import McpToolService
from app.rag.retriever import get_retriever
from app.rag.schemas import SearchFilters

mcp = FastMCP(
    "Enterprise API Intelligence Agent",
    instructions=(
        "Tools operate only on fictional local API documentation. "
        "Any mock change request requires human approval."
    ),
)


@lru_cache
def get_tool_service() -> McpToolService:
    """Create local tool dependencies once for the MCP process."""

    settings = get_settings()
    return McpToolService(retriever=get_retriever(settings))


@mcp.tool()
def search_api_catalog(
    query: str, filters: SearchFilters | None = None
) -> CatalogSearchResult:
    """Search synthetic API catalogue material using the configured hybrid RAG index."""

    return get_tool_service().search_api_catalog(query, filters)


@mcp.tool()
def get_api_details(api_name: str) -> ApiDetails:
    """Retrieve local synthetic OpenAPI metadata and operation summaries."""

    return get_tool_service().get_api_details(api_name)


@mcp.tool()
def validate_openapi_spec(spec_path: str) -> OpenAPIValidationResult:
    """Validate the basic structure of a local synthetic OpenAPI JSON or YAML file."""

    return get_tool_service().validate_openapi_spec(spec_path)


@mcp.tool()
def create_change_request_mock(
    title: str, description: str, risk_level: RiskLevel
) -> MockChangeRequest:
    """Create a synthetic pending proposal only; human approval is required."""

    return get_tool_service().create_change_request_mock(title, description, risk_level)


def main() -> None:
    """Run the local MCP server over standard input and output."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
