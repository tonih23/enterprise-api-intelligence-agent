"""Tests for corpus loading, metadata extraction, and chunk creation."""

import json
from pathlib import Path

import pytest

from app.rag.chunking import SourceDocument, chunk_document, load_documents

DATA_ROOT = Path(__file__).parents[1] / "data"


def test_load_documents_reads_docs_specs_and_extracts_metadata() -> None:
    documents = load_documents(DATA_ROOT)
    by_path = {document.source_path: document for document in documents}

    assert len(documents) == 7
    assert (
        by_path["data/docs/fake_mulesoft_api_catalogue.md"].metadata["api_name"]
        == "enterprise_api_catalogue"
    )
    assert (
        by_path["data/api_specs/hcp_search_api.openapi.yaml"].metadata["source_type"]
        == "openapi"
    )
    assert (
        by_path["data/api_specs/atlas_api_demo.postman_collection.json"].metadata[
            "source_type"
        ]
        == "postman_collection"
    )
    assert all(document.metadata["synthetic"] is True for document in documents)


def test_markdown_front_matter_is_not_added_to_searchable_text() -> None:
    document = next(
        document
        for document in load_documents(DATA_ROOT)
        if document.source_path.endswith("fake_mulesoft_api_catalogue.md")
    )

    assert document.text.startswith("# Fictional MuleSoft API Catalogue")
    assert 'document_id: "catalogue-doc-001"' not in document.text


def test_load_documents_supports_json_openapi_contracts(tmp_path: Path) -> None:
    specs_dir = tmp_path / "api_specs"
    specs_dir.mkdir()
    (specs_dir / "sample.openapi.json").write_text(
        json.dumps(
            {
                "openapi": "3.1.0",
                "info": {
                    "x-agent-metadata": {
                        "synthetic": True,
                        "domain": "testing",
                        "owner": "fictional_owner",
                        "data_classification": "synthetic_internal",
                        "system": "synthetic_system",
                        "api_name": "sample_api",
                        "version": "1.0.0",
                    }
                },
                "paths": {},
            }
        ),
        encoding="utf-8",
    )

    documents = load_documents(tmp_path)

    assert len(documents) == 1
    assert documents[0].metadata["source_type"] == "openapi"
    assert documents[0].metadata["api_name"] == "sample_api"


def test_chunk_document_preserves_metadata_source_path_and_stable_ids() -> None:
    document = SourceDocument(
        text="First retrieval section.\n\nSecond approval section.\n\nThird section.",
        metadata={
            "synthetic": True,
            "domain": "test",
            "owner": "fictional_owner",
            "data_classification": "synthetic_internal",
            "system": "test_system",
            "api_name": "test_api",
            "version": "1.0.0",
        },
        source_path="data/docs/test.md",
    )

    chunks = chunk_document(document, chunk_size=40, chunk_overlap=10)
    repeated_chunks = chunk_document(document, chunk_size=40, chunk_overlap=10)

    assert len(chunks) > 1
    assert chunks[0].source_path == document.source_path
    assert chunks[0].metadata == document.metadata
    assert [chunk.chunk_id for chunk in chunks] == [
        chunk.chunk_id for chunk in repeated_chunks
    ]


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    ((0, 0), (10, -1), (10, 10)),
)
def test_chunk_document_rejects_invalid_chunk_configuration(
    chunk_size: int, chunk_overlap: int
) -> None:
    document = SourceDocument(
        text="Synthetic body.", metadata={}, source_path="test.md"
    )

    with pytest.raises(ValueError):
        chunk_document(document, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
