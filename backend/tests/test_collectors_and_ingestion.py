from __future__ import annotations

import asyncio
import io
import stat
import zipfile
from dataclasses import asdict

import pytest
from fastapi import UploadFile

from app.core.errors import UploadValidationError
from app.services.document_processing.collector import SubmissionFileCollector
from app.services.document_processing.ingestion import (
    BidderDocumentIngestionService,
)
from conftest import (
    MemoryBidderDocumentRepository,
    make_pdf_bytes,
    make_zip_bytes,
)


SUBMISSION_ID = "11111111-1111-4111-8111-111111111111"


def collect_folder(collector, items):
    uploads = [
        UploadFile(file=io.BytesIO(content), filename=name)
        for name, content in items.items()
    ]
    return asyncio.run(collector.collect_folder(SUBMISSION_ID, uploads))


def collect_zip(collector, entries):
    upload = UploadFile(
        file=io.BytesIO(make_zip_bytes(entries)),
        filename="submission.zip",
    )
    return asyncio.run(collector.collect_zip(SUBMISSION_ID, upload))


def test_zip_and_folder_produce_identical_document_rows(
    settings_factory,
) -> None:
    documents = {
        "Bidder_A/legal/gst.pdf": make_pdf_bytes(1),
        "Bidder_A/technical/specification.pdf": make_pdf_bytes(2),
    }
    zip_settings = settings_factory("zip-storage")
    folder_settings = settings_factory("folder-storage")
    zip_repository = MemoryBidderDocumentRepository([SUBMISSION_ID])
    folder_repository = MemoryBidderDocumentRepository([SUBMISSION_ID])

    zip_collection = collect_zip(
        SubmissionFileCollector(zip_settings), documents
    )
    folder_collection = collect_folder(
        SubmissionFileCollector(folder_settings), documents
    )

    try:
        zip_records = BidderDocumentIngestionService(
            zip_repository, zip_settings
        ).ingest(SUBMISSION_ID, zip_collection)
        folder_records = BidderDocumentIngestionService(
            folder_repository, folder_settings
        ).ingest(SUBMISSION_ID, folder_collection)
    finally:
        zip_collection.cleanup()
        folder_collection.cleanup()

    assert [asdict(item) for item in zip_records] == [
        asdict(item) for item in folder_records
    ]
    assert [asdict(item) for item in zip_repository.documents[SUBMISSION_ID]] == [
        asdict(item)
        for item in folder_repository.documents[SUBMISSION_ID]
    ]


@pytest.mark.parametrize(
    "unsafe_name",
    ["../escape.pdf", "/absolute.pdf", "a/../../escape.pdf", "C:/bad.pdf"],
)
def test_zip_rejects_path_traversal(settings_factory, unsafe_name) -> None:
    collector = SubmissionFileCollector(settings_factory())
    with pytest.raises(UploadValidationError) as captured:
        collect_zip(collector, {unsafe_name: make_pdf_bytes()})
    assert captured.value.code == "UNSAFE_PATH"


def test_zip_rejects_symbolic_link(settings_factory) -> None:
    target = io.BytesIO()
    info = zipfile.ZipInfo("linked.pdf")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr(info, b"some-target")

    upload = UploadFile(file=io.BytesIO(target.getvalue()), filename="bad.zip")
    collector = SubmissionFileCollector(settings_factory())
    with pytest.raises(UploadValidationError) as captured:
        asyncio.run(collector.collect_zip(SUBMISSION_ID, upload))
    assert captured.value.code == "UNSAFE_ZIP_ENTRY"


def test_zip_rejects_non_pdf_entry(settings_factory) -> None:
    collector = SubmissionFileCollector(settings_factory())
    with pytest.raises(UploadValidationError) as captured:
        collect_zip(
            collector,
            {"legal/gst.pdf": make_pdf_bytes(), "notes.txt": b"no"},
        )
    assert captured.value.code == "PDF_ONLY"


def test_folder_rejects_unsafe_relative_path(settings_factory) -> None:
    collector = SubmissionFileCollector(settings_factory())
    with pytest.raises(UploadValidationError) as captured:
        collect_folder(collector, {"../escape.pdf": make_pdf_bytes()})
    assert captured.value.code == "UNSAFE_PATH"


def test_folder_rejects_fake_pdf(settings_factory) -> None:
    collector = SubmissionFileCollector(settings_factory())
    with pytest.raises(UploadValidationError) as captured:
        collect_folder(collector, {"legal/fake.pdf": b"not a pdf"})
    assert captured.value.code == "INVALID_PDF"


def test_folder_rejects_case_insensitive_duplicate(settings_factory) -> None:
    collector = SubmissionFileCollector(settings_factory())
    with pytest.raises(UploadValidationError) as captured:
        collect_folder(
            collector,
            {"legal/GST.pdf": make_pdf_bytes(), "legal/gst.PDF": make_pdf_bytes()},
        )
    assert captured.value.code == "DUPLICATE_PATH"
