"""Node that invokes local read-oriented MCP tool logic."""

from collections.abc import Callable
from typing import Protocol

from app.agent.state import (
    AgentState,
    CreateChangeRequestToolRequest,
    GetApiDetailsToolRequest,
    SearchCatalogToolRequest,
    SourceReference,
    ToolCallRecord,
    ValidateOpenAPIToolRequest,
)
from app.mcp_server.schemas import (
    ApiDetails,
    CatalogSearchResult,
    MockChangeRequest,
    OpenAPIValidationResult,
    RiskLevel,
)
from app.rag.schemas import SearchFilters


class LocalMcpTools(Protocol):
    """Local MCP methods required by orchestration."""

    def search_api_catalog(
        self, query: str, filters: SearchFilters | None = None
    ) -> CatalogSearchResult: ...

    def get_api_details(self, api_name: str) -> ApiDetails: ...

    def validate_openapi_spec(self, spec_path: str) -> OpenAPIValidationResult: ...

    def create_change_request_mock(
        self, title: str, description: str, risk_level: RiskLevel
    ) -> MockChangeRequest: ...


def create_mcp_node(tools: LocalMcpTools) -> Callable[[AgentState], dict[str, object]]:
    """Build a node that dispatches permitted local tool requests."""

    def invoke_tool(state: AgentState) -> dict[str, object]:
        request = state["request"]
        tool_request = request.requested_tool
        retrieved_chunks = []
        if tool_request is None:
            return {"draft_answer": "No local MCP tool request was supplied."}
        if isinstance(tool_request, CreateChangeRequestToolRequest):
            return {
                "approval_status": "pending_human_approval",
                "draft_answer": (
                    "This mock change request is approval-gated and was not executed."
                ),
            }

        try:
            if isinstance(tool_request, SearchCatalogToolRequest):
                query = tool_request.arguments.query or request.query
                filters = tool_request.arguments.filters or request.filters
                result = tools.search_api_catalog(query, filters)
                retrieved_chunks = result.search.results
                sources = [
                    SourceReference(
                        source_path=chunk.source_path,
                        chunk_id=chunk.chunk_id,
                        score=chunk.score,
                        metadata=chunk.metadata,
                    )
                    for chunk in result.search.results
                ]
                summary = (
                    f"Catalogue search returned {len(result.search.results)} "
                    "synthetic documentation chunk(s)."
                )
            elif isinstance(tool_request, GetApiDetailsToolRequest):
                result = tools.get_api_details(tool_request.arguments.api_name)
                sources = [
                    SourceReference(
                        source_path=result.source_path, metadata=result.metadata
                    )
                ]
                summary = (
                    f"Found synthetic API {result.api_name} version {result.version} "
                    f"with {len(result.operations)} operation(s)."
                )
            elif isinstance(tool_request, ValidateOpenAPIToolRequest):
                result = tools.validate_openapi_spec(tool_request.arguments.spec_path)
                sources = (
                    [
                        SourceReference(
                            source_path=result.spec_path, metadata=result.metadata
                        )
                    ]
                    if result.spec_path.startswith("data/api_specs/")
                    else []
                )
                outcome = "passed" if result.valid else "failed"
                summary = f"Local OpenAPI validation {outcome} for {result.spec_path}."
            else:
                raise ValueError(f"Unsupported local tool: {tool_request.tool_name}")
        except (RuntimeError, ValueError) as error:
            call = ToolCallRecord(
                tool_name=tool_request.tool_name,
                arguments=tool_request.arguments.model_dump(mode="json"),
                status="failed",
                result={"error": str(error)},
            )
            return {
                "tool_calls": [call],
                "draft_answer": f"Local tool execution failed: {error}",
            }

        call = ToolCallRecord(
            tool_name=tool_request.tool_name,
            arguments=tool_request.arguments.model_dump(mode="json"),
            status="completed",
            result=result.model_dump(mode="json"),
        )
        return {
            "tool_calls": [call],
            "retrieved_chunks": retrieved_chunks,
            "sources": sources,
            "draft_answer": summary,
        }

    return invoke_tool
