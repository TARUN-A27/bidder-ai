from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_submission_ingestion_service
from app.api.v1.assessments import get_assessment_service
from app.core.config import get_settings
from app.main import create_app
from app.schemas.assessment import (
    AssessmentSummaryResponse,
    ComparisonResponse,
    PersistedRequirementResult,
    SubmissionResponse,
    TenderDetailResponse,
    TenderResponse,
)
from app.schemas.submission_ingestion import SubmissionIngestionResponse
from app.services.assessment.errors import (
    AssessmentInputError,
    AssessmentNotFoundError,
)
from app.services.ingestion.errors import ManifestValidationError

from conftest import make_pdf_bytes, make_zip_bytes


TENDER_ID = "tender-001"
SUBMISSION_ID = "submission-001"


def make_tender() -> TenderResponse:
    return TenderResponse(
        tender_id=TENDER_ID,
        dataset_id="dataset-001",
        bid_number="BID-001",
        title="Demo Tender",
        buyer="Demo Buyer",
        closing_date=None,
        submission_count=1,
    )


def make_submission() -> SubmissionResponse:
    return SubmissionResponse(
        submission_id=SUBMISSION_ID,
        tender_id=TENDER_ID,
        bidder_id="bidder-001",
        bidder_name="Example Bidder",
        pan_reference="ABCDE1234F",
        dataset_id="dataset-001",
        bid_number="BID-001",
        status="UPLOADED",
        offered_model="MODEL-1",
        mse_claimed=False,
        startup_claimed=False,
        nsic_claimed=False,
        emd_exemption_claimed=False,
        assessment_available=True,
        score=80.5,
        final_risk="HIGH",
    )


def make_assessment() -> AssessmentSummaryResponse:
    results = [
        PersistedRequirementResult(
            requirement_code=f"REQ-{index:02d}",
            status="COMPLIANT",
            reason="Requirement satisfied",
            requires_human_review=False,
            evidence={},
            source_references=[],
            warnings=[],
            title=f"Requirement {index}",
            configured_weight=1.0,
            awarded_points=1.0,
        )
        for index in range(1, 17)
    ]

    return AssessmentSummaryResponse(
        score=80.5,
        base_risk="LOW",
        triggered_risk_overrides=[],
        final_risk="HIGH",
        recommendation="PROCEED_WITH_REVIEW",
        requirement_scores=[],
        configured_applicable_weight=16.0,
        configured_total_weight=16.0,
        final_decision_authority="HUMAN_PROCUREMENT_OFFICER",
        submission_id=SUBMISSION_ID,
        bidder_id="bidder-001",
        bidder_name="Example Bidder",
        tender_id=TENDER_ID,
        assessed_at="2026-09-18T00:00:00Z",
        requirement_results=results,
        advisory=True,
    )


def make_comparison() -> ComparisonResponse:
    return ComparisonResponse(
        tender_id=TENDER_ID,
        bidders=[
            {
                "submission_id": SUBMISSION_ID,
                "bidder_name": "Example Bidder",
                "score": 80.5,
                "final_risk": "HIGH",
                "recommendation": "PROCEED_WITH_REVIEW",
                "non_compliant_count": 0,
                "missing_count": 0,
                "needs_review_count": 1,
            }
        ],
    )


def make_ingestion_response(*, duplicate_import: bool = False) -> SubmissionIngestionResponse:
    return SubmissionIngestionResponse(
        submission_id=SUBMISSION_ID,
        bidder_id="bidder-001",
        bidder_name="Example Bidder",
        tender_id=TENDER_ID,
        document_count=1,
        documents=[
            {
                "document_id": "document-001",
                "document_code": None,
                "document_type": "technical_document",
                "filename": "technical.pdf",
                "normalized_filename": "technical.pdf",
                "sha256": "a" * 64,
                "size_bytes": 100,
                "page_count": 1,
                "processing_status": "UPLOADED",
            }
        ],
        warnings=[],
        status="UPLOADED",
        ready_for_assessment=True,
        duplicate_import=duplicate_import,
    )


class FakeAssessmentRepository:
    def __init__(self) -> None:
        self.tender_response = make_tender()
        self.submission_response = make_submission()
        self.assessment_response = make_assessment()

    def tenders(self):
        return [self.tender_response]

    def tender(self, tender_id: str):
        if tender_id != TENDER_ID:
            raise AssessmentNotFoundError("Tender not found")

        return TenderDetailResponse(
            **self.tender_response.model_dump(),
            requirements=[],
            technical_requirements=[],
            mandatory_documents=[],
        )

    def submissions(self, tender_id: str):
        if tender_id != TENDER_ID:
            raise AssessmentNotFoundError("Tender not found")
        return [self.submission_response]

    def submission(self, submission_id: str):
        if submission_id != SUBMISSION_ID:
            raise AssessmentNotFoundError("Submission not found")
        return self.submission_response

    def assessment(self, submission_id: str):
        if submission_id != SUBMISSION_ID:
            raise AssessmentNotFoundError("Persisted assessment not found")
        return self.assessment_response


class FakeAssessmentService:
    def __init__(self) -> None:
        self.repository = FakeAssessmentRepository()

    def run_assessment(self, submission_id: str):
        if submission_id != SUBMISSION_ID:
            raise AssessmentNotFoundError("Submission not found")
        return self.repository.assessment(submission_id)

    def comparison(self, tender_id: str):
        if tender_id != TENDER_ID:
            raise AssessmentNotFoundError("Tender not found")
        return make_comparison()


class FakeIngestionService:
    def __init__(
        self,
        *,
        duplicate_import: bool = False,
        error: Exception | None = None,
    ) -> None:
        self.duplicate_import = duplicate_import
        self.error = error
        self.calls = []

    def ingest(self, tender_id, package):
        self.calls.append((tender_id, package))

        if self.error is not None:
            raise self.error

        return make_ingestion_response(
            duplicate_import=self.duplicate_import
        )


@pytest.fixture
def contract_app(settings_factory):
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings_factory()
    yield application
    application.dependency_overrides.clear()


def test_frozen_endpoint_paths_are_registered(contract_app):
    expected_paths = {
        "/api/v1/tenders",
        "/api/v1/tenders/{tender_id}",
        "/api/v1/tenders/{tender_id}/submissions",
        "/api/v1/submissions/{submission_id}",
        "/api/v1/tenders/{tender_id}/submissions/import-zip",
        "/api/v1/tenders/{tender_id}/submissions/import-files",
        "/api/v1/tenders/{tender_id}/submissions/import-bulk-zip",
        "/api/v1/tenders/{tender_id}/submissions/import-folder",
        "/api/v1/submissions/{submission_id}/assess",
        "/api/v1/submissions/{submission_id}/assessment",
        "/api/v1/submissions/{submission_id}/requirement-results",
        "/api/v1/tenders/{tender_id}/comparison",
    }

    actual_paths = set(contract_app.openapi()["paths"])

    assert expected_paths.issubset(actual_paths)


def test_get_tenders_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get("/api/v1/tenders")

    assert response.status_code == 200
    assert response.json()[0]["tender_id"] == TENDER_ID
    assert "submission_count" in response.json()[0]


def test_get_tender_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get(
        f"/api/v1/tenders/{TENDER_ID}"
    )

    assert response.status_code == 200
    assert response.json()["tender_id"] == TENDER_ID
    assert "requirements" in response.json()
    assert "technical_requirements" in response.json()
    assert "mandatory_documents" in response.json()


def test_get_submissions_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get(
        f"/api/v1/tenders/{TENDER_ID}/submissions"
    )

    assert response.status_code == 200
    assert response.json()[0]["submission_id"] == SUBMISSION_ID


def test_get_submission_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get(
        f"/api/v1/submissions/{SUBMISSION_ID}"
    )

    assert response.status_code == 200
    assert response.json()["submission_id"] == SUBMISSION_ID
    assert response.json()["bidder_name"] == "Example Bidder"


def test_assess_submission_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).post(
        f"/api/v1/submissions/{SUBMISSION_ID}/assess"
    )

    assert response.status_code == 200
    assert response.json()["score"] == 80.5
    assert response.json()["final_risk"] == "HIGH"
    assert response.json()["advisory"] is True


def test_get_assessment_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get(
        f"/api/v1/submissions/{SUBMISSION_ID}/assessment"
    )

    assert response.status_code == 200
    assert response.json()["submission_id"] == SUBMISSION_ID
    assert len(response.json()["requirement_results"]) == 16


def test_get_requirement_results_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get(
        f"/api/v1/submissions/{SUBMISSION_ID}/requirement-results"
    )

    assert response.status_code == 200
    assert len(response.json()) == 16
    assert response.json()[0]["requirement_code"] == "REQ-01"


def test_get_comparison_success(contract_app):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get(
        f"/api/v1/tenders/{TENDER_ID}/comparison"
    )

    assert response.status_code == 200
    assert response.json()["tender_id"] == TENDER_ID
    assert response.json()["bidders"][0]["submission_id"] == SUBMISSION_ID


def test_import_zip_uses_frozen_file_field(contract_app):
    service = FakeIngestionService()
    contract_app.dependency_overrides[get_submission_ingestion_service] = (
        lambda: service
    )

    archive = make_zip_bytes(
        {
            "technical.pdf": make_pdf_bytes(),
        }
    )

    response = TestClient(contract_app).post(
        f"/api/v1/tenders/{TENDER_ID}/submissions/import-zip",
        files={
            "file": (
                "submission.zip",
                archive,
                "application/zip",
            )
        },
        data={
            "bidder_metadata": json.dumps(
                {
                    "bidder_name": "Example Bidder",
                    "pan_reference": "ABCDE1234F",
                }
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["submission_id"] == SUBMISSION_ID
    assert service.calls


def test_import_zip_missing_file_has_fastapi_validation_shape(contract_app):
    service = FakeIngestionService()
    contract_app.dependency_overrides[get_submission_ingestion_service] = (
        lambda: service
    )

    response = TestClient(contract_app).post(
        f"/api/v1/tenders/{TENDER_ID}/submissions/import-zip",
        data={
            "bidder_metadata": json.dumps(
                {
                    "bidder_name": "Example Bidder",
                    "pan_reference": "ABCDE1234F",
                }
            )
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert isinstance(detail, list)
    assert detail[0]["type"] == "missing"
    assert "file" in detail[0]["loc"]


def test_import_files_uses_repeated_files_and_bidder_profile(contract_app):
    service = FakeIngestionService()
    contract_app.dependency_overrides[get_submission_ingestion_service] = (
        lambda: service
    )

    pdf = make_pdf_bytes()

    response = TestClient(contract_app).post(
        f"/api/v1/tenders/{TENDER_ID}/submissions/import-files",
        files=[
            ("files", ("technical.pdf", pdf, "application/pdf")),
            ("files", ("commercial.pdf", pdf, "application/pdf")),
        ],
        data={
            "bidder_profile": json.dumps(
                {
                    "bidder_name": "Example Bidder",
                    "pan_reference": "ABCDE1234F",
                }
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["submission_id"] == SUBMISSION_ID
    assert service.calls

    tender_id, package = service.calls[0]

    assert tender_id == TENDER_ID
    assert len(package.documents) == 2


def test_import_files_allows_missing_bidder_profile_for_auto_discovery(
    contract_app,
):
    service = FakeIngestionService()
    contract_app.dependency_overrides[get_submission_ingestion_service] = (
        lambda: service
    )

    response = TestClient(contract_app).post(
        f"/api/v1/tenders/{TENDER_ID}/submissions/import-files",
        files=[
            (
                "files",
                ("technical.pdf", make_pdf_bytes(), "application/pdf"),
            )
        ],
    )

    assert response.status_code == 201
    assert service.calls
    _, package = service.calls[0]
    assert package.bidder is None


def test_import_files_structured_ingestion_error(contract_app):
    service = FakeIngestionService(
        error=ManifestValidationError(
            "Manifest file set mismatch (missing: example.pdf)"
        )
    )

    contract_app.dependency_overrides[get_submission_ingestion_service] = (
        lambda: service
    )

    response = TestClient(contract_app).post(
        f"/api/v1/tenders/{TENDER_ID}/submissions/import-files",
        files=[
            (
                "files",
                ("technical.pdf", make_pdf_bytes(), "application/pdf"),
            )
        ],
        data={
            "bidder_profile": json.dumps(
                {
                    "bidder_name": "Example Bidder",
                    "pan_reference": "ABCDE1234F",
                }
            )
        },
    )

    assert response.status_code == 400

    detail = response.json()["detail"]

    assert detail["code"] == "ManifestValidationError"
    assert detail["message"] == (
        "Manifest file set mismatch (missing: example.pdf)"
    )


def test_duplicate_import_returns_200(contract_app):
    service = FakeIngestionService(duplicate_import=True)

    contract_app.dependency_overrides[get_submission_ingestion_service] = (
        lambda: service
    )

    response = TestClient(contract_app).post(
        f"/api/v1/tenders/{TENDER_ID}/submissions/import-files",
        files=[
            (
                "files",
                ("technical.pdf", make_pdf_bytes(), "application/pdf"),
            )
        ],
        data={
            "bidder_profile": json.dumps(
                {
                    "bidder_name": "Example Bidder",
                    "pan_reference": "ABCDE1234F",
                }
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["duplicate_import"] is True


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        (
            "/api/v1/tenders/unknown-tender",
            "Tender not found",
        ),
        (
            "/api/v1/submissions/unknown-submission",
            "Submission not found",
        ),
    ],
)
def test_assessment_api_uses_string_error_detail(
    contract_app,
    path,
    expected_detail,
):
    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: FakeAssessmentService()
    )

    response = TestClient(contract_app).get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


def test_assessment_input_error_is_422(contract_app):
    class InvalidAssessmentService(FakeAssessmentService):
        def run_assessment(self, submission_id: str):
            raise AssessmentInputError("Runtime evidence is unavailable")

    contract_app.dependency_overrides[get_assessment_service] = (
        lambda: InvalidAssessmentService()
    )

    response = TestClient(contract_app).post(
        f"/api/v1/submissions/{SUBMISSION_ID}/assess"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Runtime evidence is unavailable"
