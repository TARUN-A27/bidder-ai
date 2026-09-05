from __future__ import annotations

import logging
from typing import Annotated

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


logger = logging.getLogger(__name__)
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
    try:
        package = await SubmissionPackageCollector(settings).collect_zip(file, bidder_metadata)
        result = await run_in_threadpool(service.ingest, tender_id, package)
        if result.duplicate_import:
            response.status_code = status.HTTP_200_OK
        return result
    except Exception as exc:
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
    try:
        package = await SubmissionPackageCollector(settings).collect_files(
            files, bidder_profile, document_manifest
        )
        result = await run_in_threadpool(service.ingest, tender_id, package)
        if result.duplicate_import:
            response.status_code = status.HTTP_200_OK
        return result
    except Exception as exc:
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
    logger.exception("Unexpected submission ingestion failure")
    raise HTTPException(500, detail={"code": "INGESTION_FAILED", "message": "Submission could not be ingested"}) from exc
