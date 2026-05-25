"""Validation tests for the fictional retrieval corpus."""

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
DOCS_DIR = ROOT / "data" / "docs"
SPECS_DIR = ROOT / "data" / "api_specs"
REQUIRED_METADATA = {
    "domain",
    "owner",
    "data_classification",
    "system",
    "api_name",
    "version",
}
MARKDOWN_ARTIFACTS = (
    "fake_mulesoft_api_catalogue.md",
    "api_governance_runbook.md",
    "incident_response_runbook.md",
    "teams_bot_architecture_notes.md",
)
OPENAPI_ARTIFACTS = (
    "hcp_search_api.openapi.yaml",
    "clinical_trials_api.openapi.yaml",
)


def assert_required_metadata(metadata: dict[str, object]) -> None:
    """Assert corpus metadata supports future retrieval filters."""

    assert REQUIRED_METADATA <= metadata.keys()
    assert metadata["synthetic"] is True
    assert all(metadata[field] for field in REQUIRED_METADATA)


@pytest.mark.parametrize("filename", MARKDOWN_ARTIFACTS)
def test_markdown_artifacts_are_labeled_synthetic_with_metadata(filename: str) -> None:
    content = (DOCS_DIR / filename).read_text(encoding="utf-8")
    _, front_matter, body = content.split("---", maxsplit=2)
    metadata = yaml.safe_load(front_matter)

    assert_required_metadata(metadata)
    assert "synthetic" in body.lower()


@pytest.mark.parametrize("filename", OPENAPI_ARTIFACTS)
def test_openapi_artifacts_include_synthetic_metadata_and_test_hosts(
    filename: str,
) -> None:
    specification = yaml.safe_load((SPECS_DIR / filename).read_text(encoding="utf-8"))
    metadata = specification["info"]["x-agent-metadata"]

    assert specification["openapi"] == "3.1.0"
    assert_required_metadata(metadata)
    assert metadata["version"] == specification["info"]["version"]
    assert all(".test" in server["url"] for server in specification["servers"])


def test_clinical_trials_write_operation_requires_human_approval() -> None:
    specification = yaml.safe_load(
        (SPECS_DIR / "clinical_trials_api.openapi.yaml").read_text(encoding="utf-8")
    )
    operation = specification["paths"]["/trial-interest-requests"]["post"]

    assert operation["x-risk-level"] == "approval_required"
    assert operation["x-human-approval-required"] is True


def test_postman_collection_is_synthetic_and_uses_runtime_token_placeholder() -> None:
    collection = json.loads(
        (SPECS_DIR / "atlas_api_demo.postman_collection.json").read_text(
            encoding="utf-8"
        )
    )
    variables = {
        variable["key"]: variable["value"] for variable in collection["variable"]
    }

    assert_required_metadata(collection["x-agent-metadata"])
    assert collection["info"]["schema"].endswith("/collection/v2.1.0/collection.json")
    assert variables["access_token"] == "replace-at-runtime"
    assert ".test" in variables["hcp_base_url"]
    assert ".test" in variables["trials_base_url"]
