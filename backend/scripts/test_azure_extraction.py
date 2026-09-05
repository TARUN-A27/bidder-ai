from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.core.config import get_settings
from app.services.document_processing.azure_document_intelligence import (
    AzureDocumentIntelligenceService,
    DocumentExtractionError,
)


DEFAULT_TEST_PDF = Path(
    "/home/tarun/TARUN/projects/test-sih-docs/"
    "bidders/Bidder_A_Low_Risk/documents/"
    "02_GST_Registration_Certificate.pdf"
)

CONTENT_PREVIEW_LENGTH = 1800


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test BidGuard Azure Document Intelligence extraction "
            "on one local PDF."
        )
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        type=Path,
        default=DEFAULT_TEST_PDF,
        help="Optional local PDF path",
    )
    return parser.parse_args()


def print_result(result) -> None:
    print("=" * 72)
    print("BIDGUARD AI — AZURE DOCUMENT EXTRACTION TEST")
    print("=" * 72)
    print(f"File name:      {result.file_name}")
    print(f"Model:          {result.model_id}")
    print(f"Page count:     {result.page_count}")
    print(f"Table count:    {result.table_count}")
    print(f"Content length: {result.metadata.content_length}")

    print()
    print("-" * 72)
    print(f"EXTRACTED TEXT — FIRST {CONTENT_PREVIEW_LENGTH} CHARACTERS")
    print("-" * 72)
    print(result.content[:CONTENT_PREVIEW_LENGTH])

    if len(result.content) > CONTENT_PREVIEW_LENGTH:
        print("\n[Content preview truncated]")

    print()
    print("-" * 72)
    print("PAGE SUMMARY")
    print("-" * 72)

    if not result.pages:
        print("No pages returned.")
    else:
        for page in result.pages:
            print(
                f"Page {page.page_number}: "
                f"{page.line_count} extracted lines"
            )

    print()
    print("-" * 72)
    print("TABLE SUMMARY")
    print("-" * 72)

    if not result.tables:
        print("No tables returned.")
    else:
        for index, table in enumerate(result.tables, start=1):
            print(
                f"Table {index}: "
                f"{table.row_count} rows x "
                f"{table.column_count} columns, "
                f"{len(table.cells)} cells"
            )


def main() -> int:
    arguments = parse_arguments()
    settings = get_settings()

    try:
        with AzureDocumentIntelligenceService(
            settings
        ) as extraction_service:
            result = extraction_service.extract(arguments.pdf_path)
    except DocumentExtractionError as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 1

    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
