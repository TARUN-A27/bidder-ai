from __future__ import annotations

import asyncio
import io
from types import SimpleNamespace

from fastapi import UploadFile

from app.repositories.submission_repository import PersistedPackage
from app.schemas.submission_ingestion import BidderImportMetadata
from app.services.ingestion.archive import SubmissionPackageCollector
from app.services.ingestion.document_classifier import (
    DocumentClassification,
    classify_document_content,
)
from app.services.ingestion.identity_discovery import IdentityDiscoveryResult
from app.services.ingestion.ingestion_service import SubmissionIngestionService
from conftest import make_pdf_bytes, make_zip_bytes


def test_single_zip_without_metadata_is_collected_for_auto_discovery(settings_factory):
    settings = settings_factory("auto-zip")
    archive = make_zip_bytes({
        "documents/03_PAN_Record_Reference.pdf": make_pdf_bytes(),
        "documents/02_GST_Registration_Certificate.pdf": make_pdf_bytes(),
    })
    upload = UploadFile(file=io.BytesIO(archive), filename="bidder.zip")

    package = asyncio.run(SubmissionPackageCollector(settings).collect_zip(upload))
    try:
        assert package.bidder is None
        assert package.manifest is None
        assert len(package.documents) == 2
    finally:
        package.cleanup()


def test_folder_without_profile_is_collected_for_auto_discovery(settings_factory):
    settings = settings_factory("auto-folder")
    uploads = [
        UploadFile(
            file=io.BytesIO(make_pdf_bytes()),
            filename="Bidder_A/documents/03_PAN_Record_Reference.pdf",
        ),
        UploadFile(
            file=io.BytesIO(make_pdf_bytes()),
            filename="Bidder_A/documents/02_GST_Registration_Certificate.pdf",
        ),
    ]

    package = asyncio.run(SubmissionPackageCollector(settings).collect_files(uploads))
    try:
        assert package.bidder is None
        assert [item.filename for item in package.documents] == [
            "02_GST_Registration_Certificate.pdf",
            "03_PAN_Record_Reference.pdf",
        ]
    finally:
        package.cleanup()


def test_bulk_zip_groups_duplicate_basenames_per_bidder(settings_factory):
    settings = settings_factory("bulk-zip")
    archive = make_zip_bytes({
        "root/bidders/Bidder_A/documents/02_GST_Registration_Certificate.pdf": make_pdf_bytes(),
        "root/bidders/Bidder_A/documents/03_PAN_Record_Reference.pdf": make_pdf_bytes(),
        "root/bidders/Bidder_B/documents/02_GST_Registration_Certificate.pdf": make_pdf_bytes(),
        "root/bidders/Bidder_B/documents/03_PAN_Record_Reference.pdf": make_pdf_bytes(),
        # Non-bidder JSON artefacts are ignored by bulk mode.
        "root/config/scoring_rules.json": b"{}",
    })
    upload = UploadFile(file=io.BytesIO(archive), filename="all-bidders.zip")

    packages = asyncio.run(SubmissionPackageCollector(settings).collect_bulk_zip(upload))
    try:
        assert [package.package_label for package in packages] == [
            "Bidder_A",
            "Bidder_B",
        ]
        assert all(len(package.documents) == 2 for package in packages)
        assert all(package.bidder is None for package in packages)
    finally:
        for package in packages:
            package.cleanup()


def test_bulk_folder_groups_relative_paths_per_bidder(settings_factory):
    settings = settings_factory("bulk-folder")
    uploads = [
        UploadFile(
            file=io.BytesIO(make_pdf_bytes()),
            filename="bidders/Bidder_A/documents/03_PAN_Record_Reference.pdf",
        ),
        UploadFile(
            file=io.BytesIO(make_pdf_bytes()),
            filename="bidders/Bidder_B/documents/03_PAN_Record_Reference.pdf",
        ),
    ]

    packages = asyncio.run(SubmissionPackageCollector(settings).collect_bulk_files(uploads))
    try:
        assert [package.package_label for package in packages] == [
            "Bidder_A",
            "Bidder_B",
        ]
    finally:
        for package in packages:
            package.cleanup()


def test_content_classifier_recognizes_identity_documents():
    assert classify_document_content(
        "GSTIN: 00SYNTH0001A1ZX\nLegal name: Example Private Limited"
    ).document_type == "GST_REGISTRATION"
    assert classify_document_content(
        "Permanent Account Number\nPAN reference: SYNTH0001A\nLegal name: Example Private Limited"
    ).document_type == "PAN_RECORD_REFERENCE"
    assert classify_document_content(
        "Udyam Registration Number\nEnterprise name: Example Private Limited"
    ).document_type == "UDYAM_REGISTRATION"


def test_ingestion_service_uses_auto_discovered_identity(settings_factory):
    settings = settings_factory("auto-service")
    upload = UploadFile(
        file=io.BytesIO(make_pdf_bytes()),
        filename="03_PAN_Record_Reference.pdf",
    )
    package = asyncio.run(
        SubmissionPackageCollector(settings).collect_files([upload])
    )

    class FakeDiscovery:
        def discover(self, collected):
            return IdentityDiscoveryResult(
                bidder=BidderImportMetadata(
                    bidder_name="Example Private Limited",
                    pan_reference="ABCDE1234F",
                    offered_model="MODEL-1",
                ),
                classifications={
                    collected.documents[0].filename.casefold(): DocumentClassification(
                        "DOC-03", "PAN_RECORD_REFERENCE"
                    )
                },
                warnings=["Bidder identity inferred from uploaded evidence"],
            )

    class MemoryRepository:
        def persist_package(self, tender_id, bidder, documents, finalize_storage):
            assert bidder.bidder_name == "Example Private Limited"
            finalize_storage("submission-1")
            document = documents[0]
            return PersistedPackage(
                bidder_id="bidder-1",
                submission_id="submission-1",
                duplicate_import=False,
                document_ids={document.filename.casefold(): "document-1"},
                storage_paths={
                    document.filename.casefold(): (
                        f"submissions/submission-1/original/{document.filename}"
                    )
                },
            )

    try:
        result = SubmissionIngestionService(
            MemoryRepository(),
            settings,
            identity_discovery=FakeDiscovery(),
        ).ingest("tender-1", package)
        assert result.bidder_name == "Example Private Limited"
        assert result.documents[0].document_type == "PAN_RECORD_REFERENCE"
        assert result.ready_for_assessment is True
        assert any("identity inferred" in warning.lower() for warning in result.warnings)
    finally:
        package.cleanup()
