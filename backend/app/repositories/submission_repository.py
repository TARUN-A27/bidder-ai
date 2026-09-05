from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

import oracledb

from app.core.errors import DatabaseUnavailableError
from app.db.oracle import acquire_connection
from app.schemas.submission_ingestion import BidderImportMetadata
from app.services.ingestion.errors import (
    BidderIdentityConflictError,
    DuplicateSubmissionError,
    TenderNotFoundError,
)


logger = logging.getLogger(__name__)
BIDDER_NAMESPACE = uuid.UUID("9b488b62-55bc-4bc8-9a39-dad8abc969d5")
SUBMISSION_NAMESPACE = uuid.UUID("825b1dde-c6ee-4502-a90a-9d477424248a")
DOCUMENT_NAMESPACE = uuid.UUID("ce9f2b74-f912-4f41-817d-5380b94594ba")


@dataclass(frozen=True, slots=True)
class SubmissionDocumentCreate:
    filename: str
    document_code: str | None
    document_type: str
    sha256: str
    page_count: int


@dataclass(frozen=True, slots=True)
class PersistedPackage:
    bidder_id: str
    submission_id: str
    duplicate_import: bool
    document_ids: dict[str, str]
    storage_paths: dict[str, str]


class SubmissionRepositoryProtocol(Protocol):
    def persist_package(
        self,
        tender_id: str,
        bidder: BidderImportMetadata,
        documents: Sequence[SubmissionDocumentCreate],
        finalize_storage: Callable[[str], None],
    ) -> PersistedPackage: ...


def _canonical(value: str) -> str:
    return " ".join(value.split()).casefold()


class OracleSubmissionRepository:
    def __init__(self, connection_factory=acquire_connection) -> None:
        self.connection_factory = connection_factory

    def persist_package(
        self,
        tender_id: str,
        bidder: BidderImportMetadata,
        documents: Sequence[SubmissionDocumentCreate],
        finalize_storage: Callable[[str], None],
    ) -> PersistedPackage:
        try:
            with self.connection_factory() as connection:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT dataset_id FROM tenders WHERE id=:id FOR UPDATE",
                            id=tender_id,
                        )
                        tender = cursor.fetchone()
                        if tender is None:
                            raise TenderNotFoundError("Tender not found")
                        if bidder.dataset_id and bidder.dataset_id != tender[0]:
                            raise BidderIdentityConflictError(
                                "Bidder metadata belongs to a different dataset"
                            )

                        bidder_id = self._upsert_bidder(cursor, tender[0], bidder)
                        submission_id, existing = self._submission(
                            cursor, tender_id, bidder_id, bidder
                        )
                        if existing:
                            self._validate_existing_submission(existing, bidder)
                        cursor.execute(
                            """SELECT id,file_name,sha256,storage_path
                               FROM bidder_documents WHERE submission_id=:id""",
                            id=submission_id,
                        )
                        existing_documents = cursor.fetchall()
                        if existing_documents:
                            return self._resolve_duplicate(
                                bidder_id, submission_id, existing_documents, documents
                            )

                        if not existing:
                            cursor.execute(
                                """INSERT INTO bid_submissions
                                   (id,tender_id,bidder_id,status,mse_claimed,startup_claimed,
                                    nsic_claimed,emd_exemption_claimed,offered_make,offered_model)
                                   VALUES (:id,:tender,:bidder,'UPLOADED',:mse,:startup,
                                           :nsic,:emd,:make,:model)""",
                                id=submission_id, tender=tender_id, bidder=bidder_id,
                                mse=int(bidder.mse_claimed), startup=int(bidder.startup_claimed),
                                nsic=int(bidder.nsic_claimed), emd=int(bidder.emd_exemption_claimed),
                                make=bidder.offered_make, model=bidder.offered_model,
                            )

                        rows = []
                        document_ids: dict[str, str] = {}
                        storage_paths: dict[str, str] = {}
                        for document in documents:
                            document_id = str(uuid.uuid5(
                                DOCUMENT_NAMESPACE,
                                f"{submission_id}|{document.filename.casefold()}|{document.sha256}",
                            ))
                            storage_path = (
                                f"submissions/{submission_id}/original/{document.filename}"
                            )
                            document_ids[document.filename.casefold()] = document_id
                            storage_paths[document.filename.casefold()] = storage_path
                            rows.append(dict(
                                id=document_id, submission_id=submission_id,
                                document_code=document.document_code,
                                document_type=document.document_type,
                                file_name=document.filename, storage_path=storage_path,
                                sha256=document.sha256, page_count=document.page_count,
                                confidence=1.0 if document.document_type != "UNKNOWN" else None,
                                upload_status="UPLOADED",
                            ))
                        cursor.executemany(
                            """INSERT INTO bidder_documents
                               (id,submission_id,document_code,document_type,file_name,
                                storage_path,sha256,page_count,classification_confidence,upload_status)
                               VALUES (:id,:submission_id,:document_code,:document_type,:file_name,
                                       :storage_path,:sha256,:page_count,:confidence,:upload_status)""",
                            rows,
                        )
                        finalize_storage(submission_id)
                    connection.commit()
                    return PersistedPackage(
                        bidder_id, submission_id, False, document_ids, storage_paths
                    )
                except Exception:
                    connection.rollback()
                    raise
        except (
            TenderNotFoundError,
            BidderIdentityConflictError,
            DuplicateSubmissionError,
            DatabaseUnavailableError,
        ):
            raise
        except oracledb.Error as exc:
            logger.exception("Oracle submission package persistence failed")
            raise DatabaseUnavailableError("Database operation failed") from exc

    @staticmethod
    def _upsert_bidder(cursor, dataset_id: str, bidder: BidderImportMetadata) -> str:
        cursor.execute(
            """SELECT id,legal_name FROM bidders
               WHERE UPPER(TRIM(pan_reference))=UPPER(TRIM(:pan)) FOR UPDATE""",
            pan=bidder.pan_reference,
        )
        matches = cursor.fetchall()
        if len(matches) > 1:
            raise BidderIdentityConflictError("Bidder PAN is not unique")
        if matches:
            if _canonical(matches[0][1]) != _canonical(bidder.bidder_name):
                raise BidderIdentityConflictError(
                    "Bidder PAN is already associated with another legal name"
                )
            return matches[0][0]
        bidder_id = str(uuid.uuid5(
            BIDDER_NAMESPACE, f"{dataset_id}|{bidder.pan_reference.upper()}"
        ))
        cursor.execute(
            """INSERT INTO bidders
               (id,legal_name,entity_type,registered_address,pan_reference,
                gst_reference,udyam_reference,is_synthetic)
               VALUES (:id,:name,:entity,:address,:pan,:gst,:udyam,:synthetic)""",
            id=bidder_id, name=bidder.bidder_name, entity=bidder.entity_type,
            address=bidder.registered_address, pan=bidder.pan_reference,
            gst=bidder.gst_reference, udyam=bidder.udyam_reference,
            synthetic=int(bidder.is_synthetic),
        )
        return bidder_id

    @staticmethod
    def _submission(cursor, tender_id, bidder_id, bidder):
        cursor.execute(
            """SELECT id,offered_model,mse_claimed,startup_claimed,
                      nsic_claimed,emd_exemption_claimed
               FROM bid_submissions
               WHERE tender_id=:tender AND bidder_id=:bidder FOR UPDATE""",
            tender=tender_id, bidder=bidder_id,
        )
        existing = cursor.fetchone()
        if existing:
            return existing[0], existing
        return str(uuid.uuid5(
            SUBMISSION_NAMESPACE, f"{tender_id}|{bidder_id}"
        )), None

    @staticmethod
    def _validate_existing_submission(existing, bidder: BidderImportMetadata) -> None:
        expected = (
            bidder.offered_model,
            int(bidder.mse_claimed),
            int(bidder.startup_claimed),
            int(bidder.nsic_claimed),
            int(bidder.emd_exemption_claimed),
        )
        if tuple(existing[1:]) != expected:
            raise BidderIdentityConflictError(
                "Existing submission metadata differs from the imported package"
            )

    @staticmethod
    def _resolve_duplicate(
        bidder_id: str,
        submission_id: str,
        existing,
        documents: Sequence[SubmissionDocumentCreate],
    ) -> PersistedPackage:
        stored = sorted(
            (row[1].casefold(), row[2]) for row in existing
        )
        incoming = sorted(
            (document.filename.casefold(), document.sha256) for document in documents
        )
        if stored != incoming:
            raise DuplicateSubmissionError(
                "This bidder already has a different package for the tender"
            )
        return PersistedPackage(
            bidder_id=bidder_id,
            submission_id=submission_id,
            duplicate_import=True,
            document_ids={row[1].casefold(): row[0] for row in existing},
            storage_paths={row[1].casefold(): row[3] for row in existing},
        )
