from __future__ import annotations

import hashlib
import io
import json
import logging
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.repositories.assessment_repository import AssessmentRepository


DATASET_ROOT = Path("/home/tarun/TARUN/projects/test-sih-docs")
BIDDER_DIRECTORIES = {
    "BIDDER_A": DATASET_ROOT / "bidders/Bidder_A_Low_Risk",
    "BIDDER_B": DATASET_ROOT / "bidders/Bidder_B_High_Risk",
    "BIDDER_C": DATASET_ROOT / "bidders/Bidder_C_Critical_Risk",
}
EXPECTED_COUNTS = {"BIDDER_A": 21, "BIDDER_B": 21, "BIDDER_C": 19}


def package_zip(directory: Path, *, omit: set[str] | None = None, extras=None) -> bytes:
    target = io.BytesIO()
    omitted = omit or set()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        prefix = directory.name
        archive.write(directory / "bidder_profile.json", f"{prefix}/bidder_profile.json")
        archive.write(directory / "document_manifest.json", f"{prefix}/document_manifest.json")
        for path in sorted((directory / "documents").glob("*.pdf")):
            if path.name not in omitted:
                archive.write(path, f"{prefix}/documents/{path.name}")
        for name, content in (extras or {}).items():
            archive.writestr(name, content)
    return target.getvalue()


def post_zip(client: TestClient, tender_id: str, payload: bytes):
    return client.post(
        f"/api/v1/tenders/{tender_id}/submissions/import-zip",
        files={"file": ("submission.zip", payload, "application/zip")},
    )


def assert_persisted(repository, settings, result, directory):
    submission_id = result["submission_id"]
    rows = repository.query(
        """SELECT id,document_code,document_type,file_name,storage_path,sha256,
                  page_count,upload_status
           FROM bidder_documents WHERE submission_id=:id ORDER BY file_name""",
        id=submission_id,
    )
    assert len(rows) == result["document_count"]
    assert all(row["file_name"].casefold().endswith(".pdf") for row in rows)
    assert all(row["upload_status"] == "UPLOADED" for row in rows)
    assert all(row["document_type"] != "UNKNOWN" for row in rows)
    source = {path.name: path for path in (directory / "documents").glob("*.pdf")}
    for row in rows:
        source_digest = hashlib.sha256(source[row["file_name"]].read_bytes()).hexdigest()
        assert row["sha256"] == source_digest
        stored = (settings.storage_root / row["storage_path"]).resolve()
        assert stored.is_relative_to(settings.storage_root.resolve())
        assert stored.is_file()
        assert hashlib.sha256(stored.read_bytes()).hexdigest() == source_digest
    extraction_count = repository.query(
        """SELECT COUNT(*) n FROM document_extractions e
           JOIN bidder_documents d ON d.id=e.document_id
           WHERE d.submission_id=:id""",
        id=submission_id,
    )[0]["n"]
    assert extraction_count == 0
    return rows


def main() -> None:
    logging.getLogger("azure").setLevel(logging.WARNING)
    settings = get_settings()
    payloads = {key: package_zip(directory) for key, directory in BIDDER_DIRECTORIES.items()}
    with TestClient(create_app()) as client:
        repository = AssessmentRepository()
        tender_response = client.get("/api/v1/tenders")
        assert tender_response.status_code == 200, tender_response.text
        tender = next(item for item in tender_response.json() if item["dataset_id"] == "SIH26100-T01")
        tender_id = tender["tender_id"]
        imported = {}

        for label, directory in BIDDER_DIRECTORIES.items():
            response = post_zip(client, tender_id, payloads[label])
            assert response.status_code in {200, 201}, response.text
            result = response.json()
            assert result["document_count"] == EXPECTED_COUNTS[label]
            assert result["ready_for_assessment"] is True
            assert result["status"] == "UPLOADED"
            assert "storage_path" not in response.text
            rows = assert_persisted(repository, settings, result, directory)
            profile = json.loads((directory / "bidder_profile.json").read_text())
            identity = profile["bidder_identity"]
            assert repository.query(
                "SELECT COUNT(*) n FROM bidders WHERE pan_reference=:pan AND legal_name=:name",
                pan=identity["pan"], name=identity["legal_name"],
            )[0]["n"] == 1
            assert repository.query(
                "SELECT COUNT(*) n FROM bid_submissions WHERE tender_id=:tender AND bidder_id=:bidder",
                tender=tender_id, bidder=result["bidder_id"],
            )[0]["n"] == 1
            imported[label] = result
            print(label, result["submission_id"], len(rows), "PDFs", "duplicate" if result["duplicate_import"] else "created")

        c_names = {item["filename"] for item in imported["BIDDER_C"]["documents"]}
        assert "09_OEM_Authorization_Letter.pdf" not in c_names

        duplicate = post_zip(client, tender_id, payloads["BIDDER_A"])
        assert duplicate.status_code == 200, duplicate.text
        assert duplicate.json()["duplicate_import"] is True
        assert duplicate.json()["submission_id"] == imported["BIDDER_A"]["submission_id"]
        assert repository.query(
            "SELECT COUNT(*) n FROM bidder_documents WHERE submission_id=:id",
            id=imported["BIDDER_A"]["submission_id"],
        )[0]["n"] == 21
        print("PASS: exact duplicate returned the existing submission without extra rows")

        directory = BIDDER_DIRECTORIES["BIDDER_A"]
        files = [
            ("files", (path.name, path.read_bytes(), "application/pdf"))
            for path in sorted((directory / "documents").glob("*.pdf"))
        ]
        folder = client.post(
            f"/api/v1/tenders/{tender_id}/submissions/import-files",
            files=files,
            data={
                "bidder_profile": (directory / "bidder_profile.json").read_text(),
                "document_manifest": (directory / "document_manifest.json").read_text(),
            },
        )
        assert folder.status_code == 200, folder.text
        assert folder.json()["duplicate_import"] is True
        assert folder.json()["document_count"] == 21
        print("PASS: folder/multi-file input used the same package representation")

        malicious = package_zip(
            directory,
            extras={"../../evil.pdf": (directory / "documents/02_GST_Registration_Certificate.pdf").read_bytes()},
        )
        response = post_zip(client, tender_id, malicious)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "UnsafeArchivePathError"
        assert not (settings.storage_root.parent / "evil.pdf").exists()
        print("PASS: ZIP-slip path rejected")

        invalid = package_zip(directory, extras={f"{directory.name}/documents/99_Fake.pdf": b"not a pdf"})
        response = post_zip(client, tender_id, invalid)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "InvalidPdfError"
        print("PASS: renamed non-PDF rejected")

        missing_name = "02_GST_Registration_Certificate.pdf"
        mismatch = package_zip(directory, omit={missing_name})
        response = post_zip(client, tender_id, mismatch)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "ManifestValidationError"
        print("PASS: strict manifest mismatch rejected")

        unknown_pdf = (directory / "documents/02_GST_Registration_Certificate.pdf").read_bytes()
        unknown = package_zip(
            directory,
            extras={f"{directory.name}/documents/99_Extra_Supporting_Document.pdf": unknown_pdf},
        )
        response = post_zip(client, tender_id, unknown)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "ManifestValidationError"
        print("PASS: unlisted unknown PDF rejected under strict manifest policy")

        response = post_zip(client, "00000000-0000-4000-8000-000000000000", payloads["BIDDER_A"])
        assert response.status_code == 404
        print("PASS: unknown tender returned 404")

        assessment = client.post(
            f"/api/v1/submissions/{imported['BIDDER_A']['submission_id']}/assess"
        )
        assert assessment.status_code == 200, assessment.text
        assert assessment.json()["score"] == 100.0
        assert assessment.json()["final_risk"] == "LOW"
        print("PASS: imported Bidder A assessed at 100.0 / LOW")

    print("PASS: bidder ZIP/folder ingestion, Oracle persistence, and API assertions passed")


if __name__ == "__main__":
    main()
