from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories.bidder_document_repository import (
    BidderDocumentRepositoryProtocol,
    OracleBidderDocumentRepository,
)
from app.services.document_processing.ingestion import (
    BidderDocumentIngestionService,
)
from app.repositories.submission_repository import (
    OracleSubmissionRepository,
    SubmissionRepositoryProtocol,
)
from app.services.ingestion.ingestion_service import SubmissionIngestionService


def get_bidder_document_repository(
) -> BidderDocumentRepositoryProtocol:
    return OracleBidderDocumentRepository()


def get_ingestion_service(
    repository: Annotated[
        BidderDocumentRepositoryProtocol,
        Depends(get_bidder_document_repository),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BidderDocumentIngestionService:
    return BidderDocumentIngestionService(repository, settings)


def get_submission_repository() -> SubmissionRepositoryProtocol:
    return OracleSubmissionRepository()


def get_submission_ingestion_service(
    repository: Annotated[
        SubmissionRepositoryProtocol,
        Depends(get_submission_repository),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SubmissionIngestionService:
    return SubmissionIngestionService(repository, settings)
