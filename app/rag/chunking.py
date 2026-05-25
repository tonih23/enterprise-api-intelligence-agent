"""Load synthetic corpus files and split them into metadata-rich chunks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_METADATA_FIELDS = {
    "domain",
    "owner",
    "data_classification",
    "system",
    "api_name",
    "version",
}


@dataclass(frozen=True)
class SourceDocument:
    """A parsed corpus source with metadata separated from searchable content."""

    text: str
    metadata: dict[str, Any]
    source_path: str


@dataclass(frozen=True)
class DocumentChunk:
    """A deterministic, indexable section of a source document."""

    chunk_id: str
    text: str
    metadata: dict[str, Any]
    source_path: str
    chunk_index: int


def _validate_metadata(metadata: dict[str, Any], path: Path) -> dict[str, Any]:
    missing = REQUIRED_METADATA_FIELDS - metadata.keys()
    if missing:
        formatted = ", ".join(sorted(missing))
        raise ValueError(f"{path} is missing metadata fields: {formatted}")
    if metadata.get("synthetic") is not True:
        raise ValueError(f"{path} must be explicitly marked synthetic")
    return metadata


def _source_path(path: Path, data_root: Path) -> str:
    return (Path(data_root.name) / path.relative_to(data_root)).as_posix()


def _load_markdown(path: Path, data_root: Path) -> SourceDocument:
    raw_text = path.read_text(encoding="utf-8")
    if not raw_text.startswith("---"):
        raise ValueError(f"{path} does not include YAML front matter")

    parts = raw_text.split("---", maxsplit=2)
    if len(parts) != 3:
        raise ValueError(f"{path} does not include complete YAML front matter")
    _, front_matter, body = parts
    try:
        metadata = yaml.safe_load(front_matter)
    except yaml.YAMLError as error:
        raise ValueError(f"{path} contains invalid YAML front matter") from error
    if not isinstance(metadata, dict):
        raise ValueError(f"{path} contains invalid YAML front matter")
    metadata["source_type"] = "markdown"

    return SourceDocument(
        text=body.strip(),
        metadata=_validate_metadata(metadata, path),
        source_path=_source_path(path, data_root),
    )


def _load_openapi(path: Path, data_root: Path) -> SourceDocument:
    raw_text = path.read_text(encoding="utf-8")
    try:
        specification = yaml.safe_load(raw_text)
    except yaml.YAMLError as error:
        raise ValueError(f"{path} contains invalid OpenAPI YAML") from error
    if not isinstance(specification, dict):
        raise ValueError(f"{path} does not contain an OpenAPI object")
    return _openapi_document(path, data_root, raw_text, specification)


def _openapi_document(
    path: Path,
    data_root: Path,
    raw_text: str,
    specification: dict[str, Any],
) -> SourceDocument:
    try:
        metadata = dict(specification["info"]["x-agent-metadata"])
    except (KeyError, TypeError) as error:
        raise ValueError(f"{path} has no info.x-agent-metadata mapping") from error
    metadata["source_type"] = "openapi"

    return SourceDocument(
        text=raw_text.strip(),
        metadata=_validate_metadata(metadata, path),
        source_path=_source_path(path, data_root),
    )


def _load_json(path: Path, data_root: Path) -> SourceDocument:
    raw_text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} contains invalid JSON") from error
    if not isinstance(document, dict):
        raise ValueError(f"{path} does not contain an object")
    if "openapi" in document:
        return _openapi_document(path, data_root, raw_text, document)
    try:
        metadata = dict(document["x-agent-metadata"])
    except (KeyError, TypeError) as error:
        raise ValueError(f"{path} has no x-agent-metadata mapping") from error
    metadata["source_type"] = "postman_collection"

    return SourceDocument(
        text=raw_text.strip(),
        metadata=_validate_metadata(metadata, path),
        source_path=_source_path(path, data_root),
    )


def load_documents(data_root: Path) -> list[SourceDocument]:
    """Load supported files from the documentation and specification folders."""

    loaders = {
        ".md": _load_markdown,
        ".yaml": _load_openapi,
        ".yml": _load_openapi,
        ".json": _load_json,
    }
    files = sorted((data_root / "docs").glob("*.md"))
    files.extend(sorted((data_root / "api_specs").glob("*")))

    documents = []
    for path in files:
        loader = loaders.get(path.suffix.lower())
        if loader is not None and path.is_file():
            documents.append(loader(path, data_root))
    if not documents:
        raise ValueError(f"No supported corpus files found under {data_root}")
    return documents


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be non-negative and less than chunk_size")

    content = text.strip()
    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        if end < len(content):
            minimum_break = start + (chunk_size // 2)
            break_at = content.rfind("\n\n", minimum_break, end)
            if break_at == -1:
                break_at = content.rfind("\n", minimum_break, end)
            if break_at == -1:
                break_at = content.rfind(" ", minimum_break, end)
            if break_at > start:
                end = break_at

        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(content):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def chunk_document(
    document: SourceDocument,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[DocumentChunk]:
    """Split one document while retaining metadata and stable identifiers."""

    chunks = []
    for chunk_index, text in enumerate(
        _split_text(document.text, chunk_size, chunk_overlap)
    ):
        digest = hashlib.sha256(
            f"{document.source_path}:{chunk_index}:{text}".encode()
        ).hexdigest()
        chunks.append(
            DocumentChunk(
                chunk_id=digest,
                text=text,
                metadata=dict(document.metadata),
                source_path=document.source_path,
                chunk_index=chunk_index,
            )
        )
    return chunks


def chunk_documents(
    documents: list[SourceDocument],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[DocumentChunk]:
    """Split all source documents into index-ready chunks."""

    chunks = []
    for document in documents:
        chunks.extend(
            chunk_document(document, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        )
    return chunks
