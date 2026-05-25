"""Index the synthetic documentation corpus in local OpenSearch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.rag.ingest import DEFAULT_DATA_ROOT, ingest_corpus  # noqa: E402


def main() -> int:
    """Run a single ingestion of the configured synthetic corpus."""

    parser = argparse.ArgumentParser(
        description="Embed and index synthetic API documentation in OpenSearch."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Corpus directory containing docs/ and api_specs/.",
    )
    arguments = parser.parse_args()

    try:
        result = ingest_corpus(get_settings(), data_root=arguments.data_root)
    except ConnectionError as error:
        print(f"Ingestion failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Indexed {result.indexed_count} chunks from {result.document_count} "
        f"documents into {result.index_name!r}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
