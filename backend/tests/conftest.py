from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.core.config import Settings
from app.core.errors import (
    SubmissionAlreadyHasDocumentsError,
    SubmissionNotFoundError,
)
from app.models.bidder_document import BidderDocumentCreate


class MemoryBidderDocumentRepository:
    def __init__(self, submission_ids: Iterable[str]) -> None:
        self.submission_ids = set(submission_ids)
        self.documents: dict[str, list[BidderDocumentCreate]] = {}

    def create_documents(
        self,
        submission_id: str,
        documents: Sequence[BidderDocumentCreate],
    ) -> None:
        if submission_id not in self.submission_ids:
            raise SubmissionNotFoundError(submission_id)
        if self.documents.get(submission_id):
            raise SubmissionAlreadyHasDocumentsError(submission_id)
        self.documents[submission_id] = list(documents)


def make_pdf_bytes(page_count: int = 1) -> bytes:
    target = io.BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    writer.write(target)
    return target.getvalue()


def make_zip_bytes(entries: dict[str, bytes]) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return target.getvalue()


@pytest.fixture
def pdf_bytes() -> bytes:
    return make_pdf_bytes()


@pytest.fixture
def settings_factory(tmp_path: Path):
    def factory(name: str = "storage", **overrides) -> Settings:
        values = {
            "storage_root": tmp_path / name,
            "max_upload_files": 10,
            "max_archive_bytes": 5 * 1024 * 1024,
            "max_pdf_bytes": 1024 * 1024,
            "max_total_pdf_bytes": 4 * 1024 * 1024,
            "max_zip_compression_ratio": 100.0,
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return factory
