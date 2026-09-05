from __future__ import annotations

import logging
from pathlib import Path
from types import TracebackType
from typing import Self

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    AnalyzeResult,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError, ClientAuthenticationError

from app.core.config import Settings
from app.schemas.document_extraction import (
    DocumentExtractionResult,
    ExtractedPage,
    ExtractedTable,
    ExtractedTableCell,
    ExtractionMetadata,
)


logger = logging.getLogger(__name__)


class DocumentExtractionError(Exception):
    """Base exception for document extraction failures."""


class DocumentFileNotFoundError(DocumentExtractionError):
    """Raised when the requested local document does not exist."""


class InvalidPdfError(DocumentExtractionError):
    """Raised when the supplied file is not a valid PDF."""


class EmptyDocumentError(DocumentExtractionError):
    """Raised when the supplied PDF file is empty."""


class AzureConfigurationError(DocumentExtractionError):
    """Raised when required Azure configuration is missing."""


class AzureDocumentAuthenticationError(DocumentExtractionError):
    """Raised when Azure rejects the configured credentials."""


class AzureDocumentServiceError(DocumentExtractionError):
    """Raised when Azure cannot process the request."""


class EmptyExtractionResultError(DocumentExtractionError):
    """Raised when Azure returns no usable extraction result."""


class AzureDocumentIntelligenceService:
    """Generic PDF extraction using Azure Document Intelligence."""

    def __init__(self, settings: Settings) -> None:
        endpoint = (
            settings.azure_document_intelligence_endpoint.strip().rstrip("/")
        )
        key = (
            settings.azure_document_intelligence_key.get_secret_value().strip()
        )
        model_id = (
            settings.azure_document_intelligence_model.strip()
            or "prebuilt-layout"
        )

        missing_variables: list[str] = []

        if not endpoint:
            missing_variables.append(
                "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
            )

        if not key:
            missing_variables.append("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if missing_variables:
            missing = ", ".join(missing_variables)
            raise AzureConfigurationError(
                f"Missing Azure configuration: {missing}"
            )

        self.model_id = model_id
        self._client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def extract(
        self,
        pdf_path: str | Path,
    ) -> DocumentExtractionResult:
        source_path = Path(pdf_path).expanduser()

        if not source_path.exists():
            raise DocumentFileNotFoundError(
                f"Document does not exist: {source_path}"
            )

        if not source_path.is_file():
            raise InvalidPdfError(
                f"Document path is not a file: {source_path}"
            )

        if source_path.suffix.lower() != ".pdf":
            raise InvalidPdfError(
                f"Only PDF documents are supported: {source_path.name}"
            )

        try:
            resolved_path = source_path.resolve(strict=True)
            document_bytes = resolved_path.read_bytes()
        except OSError as exc:
            raise DocumentExtractionError(
                f"Could not read document: {source_path}"
            ) from exc

        if not document_bytes:
            raise EmptyDocumentError(
                f"PDF document is empty: {resolved_path.name}"
            )

        if b"%PDF-" not in document_bytes[:1024]:
            raise InvalidPdfError(
                "File does not contain a valid PDF header: "
                f"{resolved_path.name}"
            )

        request = AnalyzeDocumentRequest(bytes_source=document_bytes)

        try:
            poller = self._client.begin_analyze_document(
                self.model_id,
                request,
            )
            result = poller.result()
        except ClientAuthenticationError as exc:
            logger.error(
                "Azure Document Intelligence authentication failed for %s",
                resolved_path.name,
            )
            raise AzureDocumentAuthenticationError(
                "Azure Document Intelligence authentication failed"
            ) from exc
        except AzureError as exc:
            logger.error(
                "Azure Document Intelligence request failed for %s: %s",
                resolved_path.name,
                type(exc).__name__,
            )
            raise AzureDocumentServiceError(
                "Azure Document Intelligence could not process the document"
            ) from exc

        if result is None:
            raise EmptyExtractionResultError(
                "Azure Document Intelligence returned no result"
            )

        return self._normalize_result(
            result=result,
            source_path=resolved_path,
        )

    def _normalize_result(
        self,
        result: AnalyzeResult,
        source_path: Path,
    ) -> DocumentExtractionResult:
        pages: list[ExtractedPage] = []

        for position, page in enumerate(result.pages or [], start=1):
            lines = [
                str(line.content or "") for line in (page.lines or [])
            ]

            pages.append(
                ExtractedPage(
                    page_number=page.page_number or position,
                    line_count=len(lines),
                    lines=lines,
                )
            )

        tables: list[ExtractedTable] = []

        for table in result.tables or []:
            cells = [
                ExtractedTableCell(
                    row_index=cell.row_index,
                    column_index=cell.column_index,
                    content=str(cell.content or ""),
                )
                for cell in (table.cells or [])
            ]

            tables.append(
                ExtractedTable(
                    row_count=table.row_count or 0,
                    column_count=table.column_count or 0,
                    cells=cells,
                )
            )

        content = result.content or ""

        if not content.strip():
            page_lines = [
                line
                for page in pages
                for line in page.lines
                if line.strip()
            ]
            content = "\n".join(page_lines)

        if not content.strip():
            table_values = [
                cell.content
                for table in tables
                for cell in table.cells
                if cell.content.strip()
            ]
            content = "\n".join(table_values)

        if not content.strip():
            raise EmptyExtractionResultError(
                "Azure Document Intelligence returned no usable text"
            )

        return DocumentExtractionResult(
            file_name=source_path.name,
            model_id=self.model_id,
            page_count=len(pages),
            table_count=len(tables),
            content=content,
            pages=pages,
            tables=tables,
            metadata=ExtractionMetadata(
                content_length=len(content),
                source_path=str(source_path),
            ),
        )
