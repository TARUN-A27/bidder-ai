from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_ingestion_service
from app.core.config import Settings, get_settings
from app.core.errors import (
    DatabaseUnavailableError,
    SubmissionAlreadyHasDocumentsError,
    SubmissionNotFoundError,
    SubmissionStorageConflictError,
    UploadValidationError,
)
from app.schemas.ingestion import (
    IngestedDocumentResponse,
    SubmissionIngestionResponse,
)
from app.services.document_processing.collector import (
    CollectedSubmission,
    SubmissionFileCollector,
)
from app.services.document_processing.ingestion import (
    BidderDocumentIngestionService,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/submissions", tags=["bidder documents"])


@router.post(
    "/{submission_id}/documents/zip",
    response_model=SubmissionIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_submission_zip(
    submission_id: UUID,
    archive: Annotated[UploadFile, File(description="One bidder ZIP")],
    settings: Annotated[Settings, Depends(get_settings)],
    ingestion_service: Annotated[
        BidderDocumentIngestionService,
        Depends(get_ingestion_service),
    ],
) -> SubmissionIngestionResponse:
    normalized_id = str(submission_id)
    collector = SubmissionFileCollector(settings)
    collection: CollectedSubmission | None = None

    try:
        collection = await collector.collect_zip(normalized_id, archive)
        records = await run_in_threadpool(
            ingestion_service.ingest,
            normalized_id,
            collection,
        )
        return _response(normalized_id, records)
    except Exception as exc:
        _raise_http_error(exc, normalized_id)
        raise
    finally:
        if collection is not None:
            collection.cleanup()
        await archive.close()


@router.post(
    "/{submission_id}/documents/folder",
    response_model=SubmissionIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_submission_folder(
    submission_id: UUID,
    files: Annotated[
        list[UploadFile],
        File(
            description=(
                "Bidder PDFs. Send each browser webkitRelativePath as the "
                "multipart filename to preserve folders."
            )
        ),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    ingestion_service: Annotated[
        BidderDocumentIngestionService,
        Depends(get_ingestion_service),
    ],
) -> SubmissionIngestionResponse:
    normalized_id = str(submission_id)
    collector = SubmissionFileCollector(settings)
    collection: CollectedSubmission | None = None

    try:
        collection = await collector.collect_folder(normalized_id, files)
        records = await run_in_threadpool(
            ingestion_service.ingest,
            normalized_id,
            collection,
        )
        return _response(normalized_id, records)
    except Exception as exc:
        _raise_http_error(exc, normalized_id)
        raise
    finally:
        if collection is not None:
            collection.cleanup()
        for upload in files:
            await upload.close()


def _response(
    submission_id: str,
    records: list,
) -> SubmissionIngestionResponse:
    return SubmissionIngestionResponse(
        submission_id=submission_id,
        document_count=len(records),
        documents=[
            IngestedDocumentResponse(
                id=record.id,
                relative_path=record.relative_path,
                file_name=record.file_name,
                storage_path=record.storage_path,
                sha256=record.sha256,
                page_count=record.page_count,
                upload_status=record.upload_status,
            )
            for record in records
        ],
    )


def _raise_http_error(exc: Exception, submission_id: str) -> None:
    if isinstance(exc, UploadValidationError):
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    if isinstance(exc, SubmissionNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SUBMISSION_NOT_FOUND",
                "message": "Bid submission was not found",
            },
        ) from exc
    if isinstance(exc, SubmissionAlreadyHasDocumentsError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DOCUMENTS_ALREADY_INGESTED",
                "message": "Submission already has ingested documents",
            },
        ) from exc
    if isinstance(exc, SubmissionStorageConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SUBMISSION_STORAGE_CONFLICT",
                "message": "Submission document storage already exists",
            },
        ) from exc
    if isinstance(exc, DatabaseUnavailableError):
        logger.exception(
            "Database unavailable while ingesting submission %s",
            submission_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": "Database service is unavailable",
            },
        ) from exc

    logger.exception(
        "Unexpected bidder document ingestion failure for submission %s",
        submission_id,
    )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "code": "INGESTION_FAILED",
            "message": "Bidder documents could not be ingested",
        },
    ) from exc
