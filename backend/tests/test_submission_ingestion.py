from __future__ import annotations

import asyncio
import io
import json
import zipfile
import stat
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from fastapi import UploadFile

from app.repositories.submission_repository import OracleSubmissionRepository, PersistedPackage
from app.services.ingestion.archive import parse_bidder_metadata
from app.services.ingestion.archive import SubmissionPackageCollector
from app.services.ingestion.document_classifier import classify_document
from app.services.ingestion.errors import (
    InvalidPdfError,
    InvalidSubmissionArchiveError,
    ManifestValidationError,
    UnsafeArchivePathError,
    UnsupportedFileTypeError,
)
from app.services.ingestion.ingestion_service import SubmissionIngestionService
from conftest import make_pdf_bytes, make_zip_bytes


PROFILE = {
    "dataset_id": "DATASET",
    "bidder_identity": {
        "bidder_id": "BIDDER_A", "legal_name": "Example Private Limited",
        "entity_type": "COMPANY", "registered_address": "Example address",
        "pan": "SYNTH0001A", "gstin": "GST", "udyam": "UDYAM",
    },
    "claims": {
        "mse_purchase_preference": True, "startup_turnover_relaxation": False,
        "emd_exemption": True,
    },
    "offered_product": {"brand": "Example", "model": "Scanner 1"},
}


def manifest(documents):
    return {
        "dataset_id": "DATASET", "bidder_id": "BIDDER_A",
        "bidder_name": "Example Private Limited", "document_count": len(documents),
        "documents": documents,
    }


def upload_zip(entries):
    return UploadFile(file=io.BytesIO(make_zip_bytes(entries)), filename="bid.zip")


def zip_package(collector, entries):
    return asyncio.run(collector.collect_zip(upload_zip(entries)))


class MemorySubmissionRepository:
    def persist_package(self, tender_id, bidder, documents, finalize_storage):
        finalize_storage("submission")
        return PersistedPackage(
            bidder_id="bidder", submission_id="submission", duplicate_import=False,
            document_ids={d.filename.casefold(): f"id-{index}" for index, d in enumerate(documents)},
            storage_paths={d.filename.casefold(): f"submissions/submission/original/{d.filename}" for d in documents},
        )


def package_entries(pdfs, manifest_payload=None):
    entries = {"Bidder/bidder_profile.json": json.dumps(PROFILE).encode()}
    if manifest_payload is not None:
        entries["Bidder/document_manifest.json"] = json.dumps(manifest_payload).encode()
    entries.update({f"Bidder/documents/{name}": data for name, data in pdfs.items()})
    return entries


def test_zip_and_folder_share_ingestion_representation(settings_factory):
    pdfs = {
        "02_GST_Registration_Certificate.pdf": make_pdf_bytes(),
        "99_Extra_Supporting_Document.pdf": make_pdf_bytes(2),
    }
    docs = [
        {"file_name": name} for name in pdfs
    ]
    zip_settings = settings_factory("package-zip")
    folder_settings = settings_factory("package-folder")
    zipped = zip_package(
        SubmissionPackageCollector(zip_settings),
        package_entries(pdfs, manifest(docs)),
    )
    uploads = [UploadFile(file=io.BytesIO(data), filename=f"folder/{name}") for name, data in pdfs.items()]
    folder = asyncio.run(SubmissionPackageCollector(folder_settings).collect_files(
        uploads, json.dumps(PROFILE), json.dumps(manifest(docs))
    ))
    try:
        zip_result = SubmissionIngestionService(MemorySubmissionRepository(), zip_settings).ingest("tender", zipped)
        folder_result = SubmissionIngestionService(MemorySubmissionRepository(), folder_settings).ingest("tender", folder)
        left = [item.model_dump(exclude={"document_id"}) for item in zip_result.documents]
        right = [item.model_dump(exclude={"document_id"}) for item in folder_result.documents]
        assert left == right
        assert zip_result.documents[0].document_type == "GST_REGISTRATION"
        assert zip_result.documents[1].document_type == "UNKNOWN"
        assert zip_result.warnings == ["Unknown document type retained: 99_Extra_Supporting_Document.pdf"]
    finally:
        zipped.cleanup()
        folder.cleanup()


@pytest.mark.parametrize("path", ["../../evil.pdf", "/evil.pdf", "C:/evil.pdf", "a/../evil.pdf"])
def test_package_zip_rejects_unsafe_paths(settings_factory, path):
    with pytest.raises(UnsafeArchivePathError):
        zip_package(SubmissionPackageCollector(settings_factory()), {path: make_pdf_bytes()})


def test_package_zip_rejects_symbolic_links(settings_factory):
    target = io.BytesIO()
    info = zipfile.ZipInfo("documents/linked.pdf")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(info, b"target.pdf")
    upload = UploadFile(file=io.BytesIO(target.getvalue()), filename="bid.zip")
    with pytest.raises(InvalidSubmissionArchiveError, match="symbolic links"):
        asyncio.run(SubmissionPackageCollector(settings_factory()).collect_zip(upload))


@pytest.mark.parametrize("name", ["expected_result.json", "mock_portal_data.json", "evil.exe", "nested.zip"])
def test_package_zip_rejects_prohibited_or_non_evidence_files(settings_factory, name):
    entries = package_entries({"02_GST_Registration_Certificate.pdf": make_pdf_bytes()})
    entries[f"Bidder/{name}"] = b"{}"
    with pytest.raises(UnsupportedFileTypeError):
        zip_package(SubmissionPackageCollector(settings_factory()), entries)


def test_package_rejects_renamed_non_pdf(settings_factory):
    entries = package_entries({"02_GST_Registration_Certificate.pdf": b"not-pdf"})
    with pytest.raises(InvalidPdfError):
        zip_package(SubmissionPackageCollector(settings_factory()), entries)


def test_strict_manifest_rejects_missing_or_unlisted_pdf(settings_factory):
    expected = manifest([
        {"file_name": "02_GST_Registration_Certificate.pdf"},
        {"file_name": "03_PAN_Record_Reference.pdf"},
    ])
    package = zip_package(
        SubmissionPackageCollector(settings_factory()),
        package_entries({"02_GST_Registration_Certificate.pdf": make_pdf_bytes()}, expected),
    )
    try:
        with pytest.raises(ManifestValidationError, match="missing"):
            SubmissionIngestionService(MemorySubmissionRepository(), settings_factory()).ingest("tender", package)
    finally:
        package.cleanup()


def test_strict_manifest_rejects_hash_mismatch(settings_factory):
    expected = manifest([{
        "file_name": "02_GST_Registration_Certificate.pdf",
        "sha256": "0" * 64,
    }])
    settings = settings_factory()
    package = zip_package(
        SubmissionPackageCollector(settings),
        package_entries({"02_GST_Registration_Certificate.pdf": make_pdf_bytes()}, expected),
    )
    try:
        with pytest.raises(ManifestValidationError, match="SHA256 mismatch"):
            SubmissionIngestionService(MemorySubmissionRepository(), settings).ingest("tender", package)
    finally:
        package.cleanup()


def test_unknown_pdf_without_manifest_is_retained_with_warnings(settings_factory):
    settings = settings_factory()
    package = zip_package(
        SubmissionPackageCollector(settings),
        package_entries({"99_Extra_Supporting_Document.pdf": make_pdf_bytes()}),
    )
    try:
        result = SubmissionIngestionService(MemorySubmissionRepository(), settings).ingest("tender", package)
        assert result.documents[0].document_type == "UNKNOWN"
        assert len(result.warnings) == 2
    finally:
        package.cleanup()


@pytest.mark.parametrize("filename,code", [
    ("09_OEM_Authorization_Letter.pdf", "DOC-11"),
    ("10_Offered_Model_Product_Datasheet.pdf", "DOC-12"),
    ("21_NSIC_SPR_Certificate.pdf", "DOC-10"),
    ("99_unknown.pdf", None),
])
def test_deterministic_document_classifier(filename, code):
    assert classify_document(filename).document_code == code


def test_repository_rolls_back_when_storage_finalization_fails():
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor.fetchone.side_effect = [("DATASET",), ("submission", "Scanner 1", 1, 0, 0, 1)]
    cursor.fetchall.side_effect = [[("bidder", "Example Private Limited")], []]
    connection = Mock()
    connection.cursor.return_value = cursor

    @contextmanager
    def factory():
        yield connection

    document = Mock(
        filename="02_GST_Registration_Certificate.pdf", document_code="DOC-02",
        document_type="GST_REGISTRATION", sha256="a" * 64, page_count=1,
    )
    with pytest.raises(RuntimeError, match="controlled storage failure"):
        OracleSubmissionRepository(factory).persist_package(
            "tender", parse_bidder_metadata(PROFILE), [document],
            lambda _submission_id: (_ for _ in ()).throw(RuntimeError("controlled storage failure")),
        )
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()


def test_service_removes_finalized_files_when_repository_commit_fails(settings_factory):
    class FailingRepository:
        def persist_package(self, tender_id, bidder, documents, finalize_storage):
            finalize_storage("failed-submission")
            raise RuntimeError("controlled commit failure")

    settings = settings_factory("commit-failure")
    package = zip_package(
        SubmissionPackageCollector(settings),
        package_entries({"02_GST_Registration_Certificate.pdf": make_pdf_bytes()}),
    )
    with pytest.raises(RuntimeError, match="controlled commit failure"):
        SubmissionIngestionService(FailingRepository(), settings).ingest("tender", package)
    assert not (settings.storage_root / "submissions/failed-submission/original").exists()
    package.cleanup()
