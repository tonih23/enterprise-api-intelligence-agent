"""Tests for the API health endpoint."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_returns_service_metadata() -> None:
    app = create_app(Settings(environment="test"))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Enterprise API Intelligence Agent",
        "version": "0.1.0",
        "environment": "test",
    }


def test_health_route_is_described_in_openapi_schema() -> None:
    app = create_app(Settings(environment="test"))

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/health" in schema["paths"]
    assert schema["paths"]["/health"]["get"]["tags"] == ["health"]
