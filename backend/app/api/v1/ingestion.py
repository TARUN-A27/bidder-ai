from __future__ import annotations

import logging
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_submission_ingestion_service
from app.core.config import Settings, get_settings
from app.core.errors import DatabaseUnavailableError
from app.schemas.submission_ingestion import SubmissionIngestionResponse
from app.services.ingestion.archive import CollectedPackage, SubmissionPackageCollector
from app.services.ingestion.errors import (
    BidderIdentityConflictError,
    DuplicateSubmissionError,
    IngestionMetadataError,
    InvalidPdfError,
    InvalidSubmissionArchiveError,
    ManifestValidationError,
    SubmissionStorageError,
    TenderNotFoundError,
    UnsafeArchivePathError,
    UnsupportedFileTypeError,
)
from app.services.ingestion.ingestion_service import SubmissionIngestionService


logger = logging.getLogger("bidguard.ingestion")
router = APIRouter(prefix="/tenders/{tender_id}/submissions", tags=["submission ingestion"])
Service = Annotated[SubmissionIngestionService, Depends(get_submission_ingestion_service)]


@router.post("/import-zip", response_model=SubmissionIngestionResponse, status_code=201)
async def import_zip(
    tender_id: str,
    file: Annotated[UploadFile, File(description="Bidder ZIP package")],
    service: Service,
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
    bidder_metadata: Annotated[str | None, Form()] = None,
) -> SubmissionIngestionResponse:
    package: CollectedPackage | None = None
    import_id = str(uuid4())
    started = perf_counter()
    logger.info(
        "IMPORT START | import_id=%s import_type=zip tender_id=%s archive=%s",
        import_id, tender_id, file.filename or "unknown",
    )
    try:
        package = await SubmissionPackageCollector(settings).collect_zip(file, bidder_metadata)
        logger.info(
            "IMPORT VALIDATION COMPLETE | import_id=%s import_type=zip tender_id=%s "
            "bidder_code=%s file_count=%s",
            import_id, tender_id, package.bidder.bidder_reference or "unknown",
            len(package.documents),
        )
        result = await run_in_threadpool(service.ingest, tender_id, package)
        if result.duplicate_import:
            response.status_code = status.HTTP_200_OK
        logger.info(
            "IMPORT COMPLETE | import_id=%s import_type=zip tender_id=%s submission_id=%s "
            "bidder_id=%s document_count=%s duplicate=%s duration_ms=%.1f",
            import_id, tender_id, result.submission_id, result.bidder_id,
            result.document_count, result.duplicate_import,
            (perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        logger.error(
            "IMPORT FAILED | import_id=%s import_type=zip tender_id=%s error_type=%s "
            "duration_ms=%.1f",
            import_id, tender_id, type(exc).__name__,
            (perf_counter() - started) * 1000,
        )
        _raise_http_error(exc)
        raise
    finally:
        if package:
            package.cleanup()
        await file.close()


@router.post("/import-files", response_model=SubmissionIngestionResponse, status_code=201)
async def import_files(
    tender_id: str,
    files: Annotated[list[UploadFile], File(description="Bidder PDF files")],
    bidder_profile: Annotated[str, Form(description="Bidder metadata JSON")],
    service: Service,
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
    document_manifest: Annotated[str | None, Form(description="Optional manifest JSON")] = None,
) -> SubmissionIngestionResponse:
    package: CollectedPackage | None = None
    import_id = str(uuid4())
    started = perf_counter()
    logger.info(
        "IMPORT START | import_id=%s import_type=multi_file tender_id=%s file_count=%s",
        import_id, tender_id, len(files),
    )
    try:
        package = await SubmissionPackageCollector(settings).collect_files(
            files, bidder_profile, document_manifest
        )
        logger.info(
            "IMPORT VALIDATION COMPLETE | import_id=%s import_type=multi_file tender_id=%s "
            "bidder_code=%s file_count=%s",
            import_id, tender_id, package.bidder.bidder_reference or "unknown",
            len(package.documents),
        )
        result = await run_in_threadpool(service.ingest, tender_id, package)
        if result.duplicate_import:
            response.status_code = status.HTTP_200_OK
        logger.info(
            "IMPORT COMPLETE | import_id=%s import_type=multi_file tender_id=%s submission_id=%s "
            "bidder_id=%s document_count=%s duplicate=%s duration_ms=%.1f",
            import_id, tender_id, result.submission_id, result.bidder_id,
            result.document_count, result.duplicate_import,
            (perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        logger.error(
            "IMPORT FAILED | import_id=%s import_type=multi_file tender_id=%s error_type=%s "
            "duration_ms=%.1f",
            import_id, tender_id, type(exc).__name__,
            (perf_counter() - started) * 1000,
        )
        _raise_http_error(exc)
        raise
    finally:
        if package:
            package.cleanup()
        for upload in files:
            await upload.close()


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, TenderNotFoundError):
        raise HTTPException(404, detail={"code": "TENDER_NOT_FOUND", "message": str(exc)}) from exc
    if isinstance(exc, (DuplicateSubmissionError, BidderIdentityConflictError, SubmissionStorageError)):
        raise HTTPException(409, detail={"code": type(exc).__name__, "message": str(exc)}) from exc
    if isinstance(exc, (
        InvalidSubmissionArchiveError, UnsafeArchivePathError,
        UnsupportedFileTypeError, InvalidPdfError,
        ManifestValidationError, IngestionMetadataError,
    )):
        raise HTTPException(400, detail={"code": type(exc).__name__, "message": str(exc)}) from exc
    if isinstance(exc, DatabaseUnavailableError):
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database is unavailable"}) from exc
    raise HTTPException(500, detail={"code": "INGESTION_FAILED", "message": "Submission could not be ingested"}) from exc
