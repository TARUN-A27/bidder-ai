from __future__ import annotations

from contextlib import contextmanager

import pytest

from app.core.errors import SubmissionNotFoundError
from app.models.bidder_document import BidderDocumentCreate
from app.repositories import bidder_document_repository as repository_module
from app.repositories.bidder_document_repository import (
    OracleBidderDocumentRepository,
)


class FakeCursor:
    def __init__(self, submission_exists: bool = True) -> None:
        self.submission_exists = submission_exists
        self.fetchone_results = (
            [("submission-id",), (0,)] if submission_exists else [None]
        )
        self.inserted = []
        self.closed = False

    def execute(self, _sql, **_params) -> None:
        pass

    def fetchone(self):
        return self.fetchone_results.pop(0)

    def executemany(self, _sql, values) -> None:
        self.inserted = values

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self) -> FakeCursor:
        return self.fake_cursor

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def document() -> BidderDocumentCreate:
    return BidderDocumentCreate(
        id="document-id",
        submission_id="submission-id",
        relative_path="legal/gst.pdf",
        file_name="gst.pdf",
        storage_path="submissions/submission-id/documents/legal/gst.pdf",
        sha256="a" * 64,
        page_count=1,
    )


def test_repository_inserts_canonical_rows(monkeypatch) -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)

    @contextmanager
    def fake_connection():
        yield connection

    monkeypatch.setattr(
        repository_module, "acquire_connection", fake_connection
    )
    OracleBidderDocumentRepository().create_documents(
        "submission-id", [document()]
    )

    assert connection.committed is True
    assert cursor.inserted == [
        {
            "id": "document-id",
            "submission_id": "submission-id",
            "document_code": None,
            "document_type": None,
            "file_name": "gst.pdf",
            "storage_path": (
                "submissions/submission-id/documents/legal/gst.pdf"
            ),
            "sha256": "a" * 64,
            "page_count": 1,
            "classification_confidence": None,
            "upload_status": "UPLOADED",
        }
    ]
    assert cursor.closed is True


def test_repository_reports_missing_submission(monkeypatch) -> None:
    cursor = FakeCursor(submission_exists=False)
    connection = FakeConnection(cursor)

    @contextmanager
    def fake_connection():
        yield connection

    monkeypatch.setattr(
        repository_module, "acquire_connection", fake_connection
    )
    with pytest.raises(SubmissionNotFoundError):
        OracleBidderDocumentRepository().create_documents(
            "submission-id", [document()]
        )
    assert connection.rolled_back is True
