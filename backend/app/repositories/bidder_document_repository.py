from __future__ import annotations

import logging
from typing import Protocol, Sequence

import oracledb

from app.core.errors import (
    DatabaseUnavailableError,
    SubmissionAlreadyHasDocumentsError,
    SubmissionNotFoundError,
)
from app.db.oracle import acquire_connection
from app.models.bidder_document import BidderDocumentCreate


logger = logging.getLogger(__name__)


class BidderDocumentRepositoryProtocol(Protocol):
    def create_documents(
        self,
        submission_id: str,
        documents: Sequence[BidderDocumentCreate],
    ) -> None: ...


class OracleBidderDocumentRepository:
    def create_documents(
        self,
        submission_id: str,
        documents: Sequence[BidderDocumentCreate],
    ) -> None:
        try:
            with acquire_connection() as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        SELECT id
                        FROM bid_submissions
                        WHERE id = :submission_id
                        FOR UPDATE
                        """,
                        submission_id=submission_id,
                    )
                    if cursor.fetchone() is None:
                        raise SubmissionNotFoundError(
                            f"Submission {submission_id} was not found"
                        )

                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM bidder_documents
                        WHERE submission_id = :submission_id
                        """,
                        submission_id=submission_id,
                    )
                    if cursor.fetchone()[0] > 0:
                        raise SubmissionAlreadyHasDocumentsError(
                            "Submission already has ingested documents"
                        )

                    cursor.executemany(
                        """
                        INSERT INTO bidder_documents (
                            id,
                            submission_id,
                            document_code,
                            document_type,
                            file_name,
                            storage_path,
                            sha256,
                            page_count,
                            classification_confidence,
                            upload_status
                        )
                        VALUES (
                            :id,
                            :submission_id,
                            :document_code,
                            :document_type,
                            :file_name,
                            :storage_path,
                            :sha256,
                            :page_count,
                            :classification_confidence,
                            :upload_status
                        )
                        """,
                        [
                            {
                                "id": document.id,
                                "submission_id": document.submission_id,
                                "document_code": document.document_code,
                                "document_type": document.document_type,
                                "file_name": document.file_name,
                                "storage_path": document.storage_path,
                                "sha256": document.sha256,
                                "page_count": document.page_count,
                                "classification_confidence": (
                                    document.classification_confidence
                                ),
                                "upload_status": document.upload_status,
                            }
                            for document in documents
                        ],
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    cursor.close()
        except (
            SubmissionNotFoundError,
            SubmissionAlreadyHasDocumentsError,
            DatabaseUnavailableError,
        ):
            raise
        except oracledb.Error as exc:
            logger.exception(
                "Oracle bidder document insert failed for submission %s",
                submission_id,
            )
            raise DatabaseUnavailableError(
                "Database operation failed"
            ) from exc
