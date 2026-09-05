from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path, PurePosixPath

from app.core.config import Settings
from app.core.errors import SubmissionStorageConflictError
from app.models.bidder_document import BidderDocumentCreate
from app.repositories.bidder_document_repository import (
    BidderDocumentRepositoryProtocol,
)
from app.services.document_processing.collector import CollectedSubmission


DOCUMENT_ID_NAMESPACE = uuid.UUID("d8fe13a6-bcd2-4a8e-84f9-f0a2daaaed98")


class BidderDocumentIngestionService:
    """Persist a canonical PDF collection, independent of upload method."""

    def __init__(
        self,
        repository: BidderDocumentRepositoryProtocol,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.settings = settings

    def ingest(
        self,
        submission_id: str,
        collection: CollectedSubmission,
    ) -> list[BidderDocumentCreate]:
        final_root = (
            self.settings.storage_root
            / "submissions"
            / submission_id
            / "documents"
        ).resolve()

        if final_root.exists():
            raise SubmissionStorageConflictError(
                "Submission document storage already exists"
            )

        final_root.mkdir(parents=True, exist_ok=False)
        records: list[BidderDocumentCreate] = []

        try:
            for document in sorted(
                collection.documents,
                key=lambda item: item.relative_path.casefold(),
            ):
                parts = PurePosixPath(document.relative_path).parts
                destination = (final_root / Path(*parts)).resolve()
                if not destination.is_relative_to(final_root):
                    raise SubmissionStorageConflictError(
                        "Document destination escaped submission storage"
                    )

                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(document.local_path, destination)

                storage_path = (
                    PurePosixPath("submissions")
                    / submission_id
                    / "documents"
                    / PurePosixPath(document.relative_path)
                ).as_posix()
                document_id = str(
                    uuid.uuid5(
                        DOCUMENT_ID_NAMESPACE,
                        "|".join(
                            (
                                submission_id,
                                document.relative_path.casefold(),
                                document.sha256,
                            )
                        ),
                    )
                )
                records.append(
                    BidderDocumentCreate(
                        id=document_id,
                        submission_id=submission_id,
                        relative_path=document.relative_path,
                        file_name=PurePosixPath(
                            document.relative_path
                        ).name,
                        storage_path=storage_path,
                        sha256=document.sha256,
                        page_count=document.page_count,
                    )
                )

            self.repository.create_documents(submission_id, records)
        except Exception:
            shutil.rmtree(final_root, ignore_errors=True)
            raise

        return records
