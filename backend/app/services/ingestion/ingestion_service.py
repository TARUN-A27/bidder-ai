from __future__ import annotations

import os
import hashlib
import shutil
from pathlib import Path

from app.repositories.submission_repository import (
    SubmissionDocumentCreate,
    SubmissionRepositoryProtocol,
)
from app.schemas.submission_ingestion import (
    IngestedSubmissionDocument,
    SubmissionIngestionResponse,
)
from app.services.ingestion.archive import CollectedPackage
from app.services.ingestion.document_classifier import classify_document
from app.services.ingestion.errors import (
    ManifestValidationError,
    SubmissionStorageError,
)


class SubmissionIngestionService:
    def __init__(self, repository: SubmissionRepositoryProtocol, settings) -> None:
        self.repository = repository
        self.settings = settings

    def ingest(
        self,
        tender_id: str,
        package: CollectedPackage,
    ) -> SubmissionIngestionResponse:
        warnings = self._validate_manifest(package)
        classified = [
            (document, classify_document(document.filename))
            for document in package.documents
        ]
        warnings.extend(
            f"Unknown document type retained: {document.filename}"
            for document, classification in classified
            if classification.document_type == "UNKNOWN"
        )
        creates = [
            SubmissionDocumentCreate(
                filename=document.filename,
                document_code=classification.document_code,
                document_type=classification.document_type,
                sha256=document.sha256,
                page_count=document.page_count,
            )
            for document, classification in classified
        ]
        moved_root: Path | None = None

        def finalize(submission_id: str) -> None:
            nonlocal moved_root
            parent = (self.settings.storage_root / "submissions" / submission_id).resolve()
            final_root = (parent / "original").resolve()
            storage_root = self.settings.storage_root.resolve()
            if not final_root.is_relative_to(storage_root):
                raise SubmissionStorageError("Final submission storage path is unsafe")
            if final_root.exists():
                raise SubmissionStorageError("Submission storage already exists")
            parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(package.payload_root, final_root)
            except OSError as exc:
                raise SubmissionStorageError("Could not finalize submission storage") from exc
            moved_root = final_root

        try:
            persisted = self.repository.persist_package(
                tender_id, package.bidder, creates, finalize
            )
        except Exception:
            if moved_root is not None:
                shutil.rmtree(moved_root, ignore_errors=True)
            raise

        if persisted.duplicate_import:
            self._verify_existing_storage(persisted.storage_paths, package)
        documents = []
        for document, classification in classified:
            identity = document.filename.casefold()
            documents.append(IngestedSubmissionDocument(
                document_id=persisted.document_ids[identity],
                document_code=classification.document_code,
                document_type=classification.document_type,
                filename=document.filename,
                normalized_filename=document.filename,
                sha256=document.sha256,
                size_bytes=document.size_bytes,
                page_count=document.page_count,
                processing_status="UPLOADED",
            ))
        return SubmissionIngestionResponse(
            submission_id=persisted.submission_id,
            bidder_id=persisted.bidder_id,
            bidder_name=package.bidder.bidder_name,
            tender_id=tender_id,
            document_count=len(documents),
            documents=documents,
            warnings=warnings,
            status="UPLOADED",
            ready_for_assessment=bool(documents),
            duplicate_import=persisted.duplicate_import,
        )

    @staticmethod
    def _validate_manifest(package: CollectedPackage) -> list[str]:
        manifest = package.manifest
        bidder = package.bidder
        if manifest is None:
            return ["No document manifest supplied; file-set matching was not performed"]
        if manifest.dataset_id and bidder.dataset_id and manifest.dataset_id != bidder.dataset_id:
            raise ManifestValidationError("Manifest dataset does not match bidder metadata")
        if bidder.bidder_reference and manifest.bidder_id != bidder.bidder_reference:
            raise ManifestValidationError("Manifest bidder identifier does not match bidder metadata")
        if " ".join(manifest.bidder_name.split()).casefold() != " ".join(bidder.bidder_name.split()).casefold():
            raise ManifestValidationError("Manifest bidder name does not match bidder metadata")
        manifest_names = [item.file_name.casefold() for item in manifest.documents]
        if len(manifest_names) != len(set(manifest_names)):
            raise ManifestValidationError("Manifest contains duplicate document filenames")
        if manifest.document_count != len(manifest.documents):
            raise ManifestValidationError("Manifest document count does not match its entries")
        for item in manifest.documents:
            candidate = item.file_name
            if (not candidate or "\\" in candidate or "/" in candidate
                    or candidate in {".", ".."} or Path(candidate).name != candidate):
                raise ManifestValidationError("Manifest document filenames must be safe basenames")
        actual = {item.filename.casefold(): item for item in package.documents}
        expected = {item.file_name.casefold(): item for item in manifest.documents}
        if set(actual) != set(expected):
            missing = sorted(set(expected) - set(actual))
            unlisted = sorted(set(actual) - set(expected))
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unlisted:
                details.append("unlisted: " + ", ".join(unlisted))
            raise ManifestValidationError("Manifest file set mismatch (" + "; ".join(details) + ")")
        if manifest.document_count != len(actual):
            raise ManifestValidationError("Manifest document count does not match uploaded PDFs")
        for name, entry in expected.items():
            document = actual[name]
            if entry.sha256 and entry.sha256.casefold() != document.sha256:
                raise ManifestValidationError(f"Manifest SHA256 mismatch: {entry.file_name}")
            if entry.page_count is not None and entry.page_count != document.page_count:
                raise ManifestValidationError(f"Manifest page count mismatch: {entry.file_name}")
        return []

    def _verify_existing_storage(self, paths: dict[str, str], package: CollectedPackage) -> None:
        root = self.settings.storage_root.resolve()
        for document in package.documents:
            relative = paths.get(document.filename.casefold())
            if not relative:
                raise SubmissionStorageError("Existing document storage metadata is incomplete")
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise SubmissionStorageError("Existing document file is unavailable")
            digest = hashlib.sha256()
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != document.sha256:
                raise SubmissionStorageError("Existing document file hash differs from metadata")
