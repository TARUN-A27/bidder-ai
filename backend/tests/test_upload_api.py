from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_bidder_document_repository
from app.core.config import get_settings
from app.main import app
from conftest import (
    MemoryBidderDocumentRepository,
    make_pdf_bytes,
    make_zip_bytes,
)


def make_client(settings, repository) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_bidder_document_repository] = lambda: repository
    return TestClient(app)


def test_health(settings_factory) -> None:
    repository = MemoryBidderDocumentRepository([])
    with make_client(settings_factory(), repository) as client:
        response = client.get("/health")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "BidGuard AI"}


def test_folder_upload_preserves_relative_paths(settings_factory) -> None:
    submission_id = str(uuid4())
    repository = MemoryBidderDocumentRepository([submission_id])
    settings = settings_factory()

    with make_client(settings, repository) as client:
        response = client.post(
            f"/api/v1/submissions/{submission_id}/documents/folder",
            files=[
                (
                    "files",
                    (
                        "Bidder_A/legal/gst.pdf",
                        make_pdf_bytes(),
                        "application/pdf",
                    ),
                ),
                (
                    "files",
                    (
                        "Bidder_A/technical/spec.pdf",
                        make_pdf_bytes(2),
                        "application/pdf",
                    ),
                ),
            ],
        )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["document_count"] == 2
    assert [item["relative_path"] for item in body["documents"]] == [
        "Bidder_A/legal/gst.pdf",
        "Bidder_A/technical/spec.pdf",
    ]
    assert len(repository.documents[submission_id]) == 2


def test_zip_upload_uses_same_response_shape(settings_factory) -> None:
    submission_id = str(uuid4())
    repository = MemoryBidderDocumentRepository([submission_id])
    archive = make_zip_bytes(
        {"Bidder_A/legal/gst.pdf": make_pdf_bytes()}
    )

    with make_client(settings_factory(), repository) as client:
        response = client.post(
            f"/api/v1/submissions/{submission_id}/documents/zip",
            files={
                "archive": (
                    "submission.zip",
                    archive,
                    "application/zip",
                )
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["document_count"] == 1
    assert body["documents"][0]["relative_path"] == (
        "Bidder_A/legal/gst.pdf"
    )


def test_zip_upload_rejects_traversal_at_api_boundary(settings_factory) -> None:
    submission_id = str(uuid4())
    repository = MemoryBidderDocumentRepository([submission_id])
    archive = make_zip_bytes({"../escape.pdf": make_pdf_bytes()})

    with make_client(settings_factory(), repository) as client:
        response = client.post(
            f"/api/v1/submissions/{submission_id}/documents/zip",
            files={"archive": ("bad.zip", archive, "application/zip")},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSAFE_PATH"
    assert repository.documents == {}


def test_missing_submission_returns_404_and_removes_files(
    settings_factory,
) -> None:
    submission_id = str(uuid4())
    repository = MemoryBidderDocumentRepository([])
    settings = settings_factory()

    with make_client(settings, repository) as client:
        response = client.post(
            f"/api/v1/submissions/{submission_id}/documents/folder",
            files={
                "files": (
                    "gst.pdf",
                    make_pdf_bytes(),
                    "application/pdf",
                )
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 404
    final_root = (
        settings.storage_root
        / "submissions"
        / submission_id
        / "documents"
    )
    assert not final_root.exists()
