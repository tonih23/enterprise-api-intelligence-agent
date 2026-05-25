"""Contract tests for the local Docker Compose stack."""

from pathlib import Path

import yaml

COMPOSE_FILE = Path(__file__).parents[1] / "docker-compose.yml"


def load_services() -> dict[str, object]:
    """Load the declared Compose services."""

    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    return compose["services"]


def test_compose_defines_required_services_and_ports() -> None:
    services = load_services()

    assert set(services) == {"api", "postgres", "opensearch", "phoenix"}
    assert "${API_PORT:-8000}:8000" in services["api"]["ports"]
    assert "${POSTGRES_PORT:-5432}:5432" in services["postgres"]["ports"]
    assert "${OPENSEARCH_PORT:-9200}:9200" in services["opensearch"]["ports"]
    assert "${PHOENIX_PORT:-6006}:6006" in services["phoenix"]["ports"]


def test_compose_uses_local_opensearch_and_phoenix_postgres_settings() -> None:
    services = load_services()

    opensearch_environment = services["opensearch"]["environment"]
    phoenix_environment = services["phoenix"]["environment"]

    assert opensearch_environment["discovery.type"] == "single-node"
    assert opensearch_environment["DISABLE_SECURITY_PLUGIN"] == "true"
    assert phoenix_environment["PHOENIX_POSTGRES_HOST"] == "postgres"
    assert phoenix_environment["PHOENIX_SQL_DATABASE_SCHEMA"] == "phoenix"
