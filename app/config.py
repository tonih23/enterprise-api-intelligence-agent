"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
EmbeddingBackend = Literal["sentence_transformers", "local_hashing"]
RouterBackend = Literal["deterministic"]
LlmProvider = Literal["none", "gemini"]
TracingBackend = Literal["none", "phoenix", "langsmith"]


class Settings(BaseSettings):
    """Runtime configuration for the API service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="API_AGENT_",
        extra="ignore",
    )

    app_name: str = "Enterprise API Intelligence Agent"
    app_version: str = "0.1.0"
    environment: Environment = "local"
    debug: bool = False
    log_level: LogLevel = "INFO"
    opensearch_url: str = "http://127.0.0.1:9200"
    opensearch_index_name: str = "api_document_chunks"
    opensearch_username: str | None = None
    opensearch_password: SecretStr | None = None
    opensearch_verify_certs: bool = False
    embedding_backend: EmbeddingBackend = "local_hashing"
    embedding_model_name: str = "BAAI/bge-large-en-v1.5"
    embedding_batch_size: int = Field(default=32, ge=1)
    router_backend: RouterBackend = "deterministic"
    llm_provider: LlmProvider = "none"
    llm_model: str = "gemini-2.5-flash"
    tracing_backend: TracingBackend = "none"
    enable_tracing: bool = Field(default=False, validation_alias="ENABLE_TRACING")
    phoenix_collector_endpoint: str = Field(
        default="http://127.0.0.1:6006/v1/traces",
        validation_alias="PHOENIX_COLLECTOR_ENDPOINT",
    )
    langsmith_project: str = Field(
        default="enterprise-api-intelligence-agent",
        validation_alias="LANGSMITH_PROJECT",
    )
    rag_chunk_size: int = Field(default=1000, ge=100)
    rag_chunk_overlap: int = Field(default=150, ge=0)

    @model_validator(mode="after")
    def validate_chunking_configuration(self) -> "Settings":
        """Reject overlap settings that cannot make forward progress."""

        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("rag_chunk_overlap must be smaller than rag_chunk_size")
        return self

    @property
    def effective_tracing_backend(self) -> TracingBackend:
        """Resolve explicit tracing configuration with legacy Phoenix support."""

        if "tracing_backend" in self.model_fields_set:
            return self.tracing_backend
        return "phoenix" if self.enable_tracing else self.tracing_backend


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for application dependencies."""

    return Settings()
