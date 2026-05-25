"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.agent.api import router as agent_router
from app.config import Settings, get_settings
from app.health import router as health_router
from app.rag.retriever import router as rag_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application with its configured routes."""

    configured_settings = settings or get_settings()
    application = FastAPI(
        title=configured_settings.app_name,
        version=configured_settings.app_version,
        debug=configured_settings.debug,
        description=(
            "Enterprise-style API intelligence agent using synthetic "
            "documentation and governed tool patterns."
        ),
    )
    application.include_router(health_router)
    application.include_router(rag_router)
    application.include_router(agent_router)

    if settings is not None:

        def override_settings() -> Settings:
            return configured_settings

        application.dependency_overrides[get_settings] = override_settings

    return application


app = create_app()
