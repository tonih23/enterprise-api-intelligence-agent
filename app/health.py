"""Health-check endpoint for the API service."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.config import Environment, Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Public health response returned by the service."""

    status: Literal["ok"]
    service: str
    version: str
    environment: Environment


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check API process health",
)
def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Confirm that the API process is running and configured."""

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
