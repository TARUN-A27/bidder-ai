from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import NAMESPACE_URL, uuid5

import pytest
from fastapi.testclient import TestClient

from app.api.v1.assessments import get_assessment_service
from app.main import create_app
from app.repositories.assessment_repository import AssessmentRepository
from app.schemas.assessment import AssessmentSummaryResponse, PersistedRequirementResult
from app.services.assessment.errors import AssessmentInputError, AssessmentNotFoundError, AssessmentStateError
from app.services.assessment.assessment_service import AssessmentService
from app.services.assessment.prototype_evidence import PrototypeEvidenceProvider
from app.schemas.compliance import BidderSubmissionManifest
from app.schemas.verification_evidence import VerificationEvidenceBundle, GstRegistryEvidence


def summary():
    return AssessmentSummaryResponse(
        submission_id="submission", bidder_id="bidder", bidder_name="Example Ltd", tender_id="tender",
        score=100, base_risk="LOW", final_risk="LOW", recommendation="Advisory recommendation",
        triggered_risk_overrides=[], requirement_scores=[], configured_applicable_weight=100,
        configured_total_weight=100, final_decision_authority="HUMAN_PROCUREMENT_OFFICER",
        assessed_at=datetime.now(timezone.utc), requirement_results=[PersistedRequirementResult(
            requirement_code=f"R-{i}", status="COMPLIANT", reason="Verified", title=f"Rule {i}",
            configured_weight=1, awarded_points=1, evidence={"value": 10}) for i in range(16)])


@pytest.mark.parametrize("fail_at", [None, "verification_checks", "requirement_results", "risk_assessments", "audit_events"])
def test_atomic_replacement_and_rollback(fail_at):
    executed = []
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor.fetchone.return_value = ("tender", "bidder")
    cursor.fetchall.side_effect = [[(f"R-{i}", str(i)) for i in range(16)], [("MOCK_GST_REGISTRY", "source")]]

    def execute(sql, **binds):
        executed.append(sql)
        if fail_at and f"INSERT INTO {fail_at}" in sql:
            raise RuntimeError("Controlled write failure")

    cursor.execute.side_effect = execute
    connection = Mock()
    connection.cursor.return_value = cursor

    @contextmanager
    def factory():
        yield connection

    verification = VerificationEvidenceBundle(dataset_id="test", bidder_id="test",
        canonical_identity_reference="test", snapshot_at=datetime.now(timezone.utc),
        gst=GstRegistryEvidence(source_key="gst", source_system="MOCK_GST_REGISTRY", status="ACTIVE"))
    repository = AssessmentRepository(factory)
    if fail_at:
        with pytest.raises(RuntimeError, match="Controlled"):
            repository.persist(summary(), verification)
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
    else:
        repository.persist(summary(), verification)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
    assert "FOR UPDATE" in executed[0]
    assert not any("DELETE FROM bidder_documents" in sql or "DELETE FROM bid_submissions" in sql for sql in executed)
    assert any("DELETE FROM requirement_results" in sql for sql in executed)


def test_read_assessment_does_not_run_pipeline():
    service = Mock()
    service.repository.assessment.return_value = summary()
    app = create_app()
    app.dependency_overrides[get_assessment_service] = lambda: service
    client = TestClient(app)
    response = client.get("/api/v1/submissions/submission/assessment")
    assert response.status_code == 200
    assert response.json()["advisory"] is True
    service.run_assessment.assert_not_called()
    service.evidence_provider.load.assert_not_called()


def test_persisted_timestamp_restores_utc_without_losing_precision():
    original = summary()
    repository = AssessmentRepository()
    repository.query = Mock(return_value=[dict(
        details_json=json.dumps({"assessment": original.model_dump(mode="json")}),
        compliance_score=original.score, base_risk=original.base_risk,
        final_risk=original.final_risk,
        calculated_at=original.assessed_at.replace(tzinfo=None))])
    assert repository.assessment(original.submission_id) == original


def test_missing_prototype_evidence_is_an_input_error(tmp_path):
    provider = PrototypeEvidenceProvider(
        SimpleNamespace(prototype_dataset_root=tmp_path), lambda _submission_id: []
    )
    with pytest.raises(AssessmentInputError, match="No unique prototype evidence"):
        provider.load(Mock())


def evidence_provider(tmp_path, records, *, fallback=True):
    prototype_root = tmp_path / "prototype"
    storage_root = tmp_path / "uploads"
    settings = SimpleNamespace(
        prototype_dataset_root=prototype_root,
        storage_root=storage_root,
        allow_preseeded_prototype_document_fallback=fallback,
    )
    return PrototypeEvidenceProvider(settings, lambda _submission_id: records), prototype_root, storage_root


def manifest_for(documents):
    return BidderSubmissionManifest(
        bidder_id="BIDDER_A", bidder_name="Example", document_count=len(documents),
        documents=documents,
    )


def test_imported_documents_are_the_exclusive_assessment_source(tmp_path):
    content = b"imported evidence"
    digest = hashlib.sha256(content).hexdigest()
    submission_id = "submission"
    storage_path = f"submissions/{submission_id}/original/02_GST.pdf"
    provider, prototype_root, storage_root = evidence_provider(tmp_path, [{
        "file_name": "02_GST.pdf", "storage_path": storage_path, "sha256": digest,
        "page_count": 2, "upload_status": "UPLOADED",
    }])
    stored = storage_root / storage_path
    stored.parent.mkdir(parents=True)
    stored.write_bytes(content)
    external = prototype_root / "bidders/Bidder_A/documents/02_GST.pdf"
    external.parent.mkdir(parents=True)
    external.write_bytes(b"different external fixture")
    manifest = manifest_for([{
        "document_number": "02", "file_name": "02_GST.pdf", "page_count": 2,
        "sha256": digest,
    }])

    paths = provider._document_paths(
        SimpleNamespace(submission_id=submission_id), external.parent.parent,
        {"synthetic": True}, manifest,
    )

    assert paths == {"02_gst.pdf": stored.resolve()}


def test_incomplete_stored_uploads_never_mix_with_prototype_files(tmp_path):
    content = b"first imported evidence"
    digest = hashlib.sha256(content).hexdigest()
    submission_id = "submission"
    storage_path = f"submissions/{submission_id}/original/02_GST.pdf"
    records = [{
        "file_name": "02_GST.pdf", "storage_path": storage_path, "sha256": digest,
        "page_count": 1, "upload_status": "UPLOADED",
    }]
    provider, prototype_root, storage_root = evidence_provider(tmp_path, records)
    stored = storage_root / storage_path
    stored.parent.mkdir(parents=True)
    stored.write_bytes(content)
    external_root = prototype_root / "bidders/Bidder_A/documents"
    external_root.mkdir(parents=True)
    (external_root / "02_GST.pdf").write_bytes(content)
    (external_root / "03_PAN.pdf").write_bytes(b"second fixture evidence")
    manifest = manifest_for([
        {"document_number": "02", "file_name": "02_GST.pdf", "sha256": digest},
        {"document_number": "03", "file_name": "03_PAN.pdf"},
    ])

    with pytest.raises(AssessmentInputError, match="document set differs"):
        provider._document_paths(
            SimpleNamespace(submission_id=submission_id), external_root.parent,
            {"synthetic": True}, manifest,
        )


def test_mismatched_stored_upload_fails_integrity_validation(tmp_path):
    submission_id = "submission"
    storage_path = f"submissions/{submission_id}/original/02_GST.pdf"
    provider, prototype_root, storage_root = evidence_provider(tmp_path, [{
        "file_name": "02_GST.pdf", "storage_path": storage_path, "sha256": "0" * 64,
        "page_count": 1, "upload_status": "UPLOADED",
    }])
    stored = storage_root / storage_path
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"tampered")
    manifest = manifest_for([{"document_number": "02", "file_name": "02_GST.pdf"}])

    with pytest.raises(AssessmentInputError, match="integrity validation"):
        provider._document_paths(
            SimpleNamespace(submission_id=submission_id), prototype_root,
            {"synthetic": True}, manifest,
        )


def test_preseeded_fallback_is_explicit_and_synthetic_only(tmp_path):
    provider, prototype_root, _ = evidence_provider(tmp_path, [], fallback=False)
    manifest = manifest_for([{"document_number": "02", "file_name": "02_GST.pdf"}])
    with pytest.raises(AssessmentInputError, match="Stored assessment documents are unavailable"):
        provider._document_paths(
            SimpleNamespace(submission_id="submission"), prototype_root,
            {"synthetic": True}, manifest,
        )


def test_preseeded_synthetic_fallback_uses_validated_prototype_documents(tmp_path):
    provider, prototype_root, _ = evidence_provider(tmp_path, [], fallback=True)
    document_root = prototype_root / "bidders/Bidder_A/documents"
    document_root.mkdir(parents=True)
    document = document_root / "02_GST.pdf"
    document.write_bytes(b"prototype evidence")
    digest = hashlib.sha256(document.read_bytes()).hexdigest()
    manifest = manifest_for([{
        "document_number": "02", "file_name": document.name, "sha256": digest,
    }])

    tender_id = "tender"
    bidder_id = "bidder"
    submission_id = str(uuid5(NAMESPACE_URL, f"{tender_id}::{bidder_id}::submission"))
    paths = provider._document_paths(
        SimpleNamespace(
            submission_id=submission_id, tender_id=tender_id, bidder_id=bidder_id,
        ), document_root.parent,
        {"synthetic": True}, manifest,
    )

    assert paths == {document.name.casefold(): document.resolve()}


def test_imported_submission_with_no_document_rows_never_uses_fallback(tmp_path):
    provider, prototype_root, _ = evidence_provider(tmp_path, [], fallback=True)
    manifest = manifest_for([{"document_number": "02", "file_name": "02_GST.pdf"}])

    with pytest.raises(AssessmentInputError, match="Stored assessment documents are unavailable"):
        provider._document_paths(
            SimpleNamespace(
                submission_id="normal-import-id", tender_id="tender", bidder_id="bidder",
            ), prototype_root, {"synthetic": True}, manifest,
        )


@pytest.mark.parametrize("invalid", ["state", "verification", "model", "weights"])
def test_invalid_runtime_inputs_never_write(invalid):
    repository = Mock()
    repository.submission.return_value = SimpleNamespace(
        bidder_name="Example", pan_reference="PAN", offered_model="Model",
        status="CANCELLED" if invalid == "state" else "UPLOADED",
        dataset_id="dataset", bid_number="bid", tender_id="tender")
    repository.tender.return_value = {"requirements": [{"requirement_code": "R-1", "weight": 100}]}
    context = SimpleNamespace(dataset_id="dataset", bid_number="bid", requirement_codes=["R-1"])
    bidder = SimpleNamespace(legal_name="Example", pan_reference="PAN", bidder_id="bidder",
                             offered_model="Other" if invalid == "model" else "Model")
    verification = SimpleNamespace(dataset_id="dataset", bidder_id="other" if invalid == "verification" else "bidder")
    rules = SimpleNamespace(dataset_id="dataset", requirement_weights={"R-2" if invalid == "weights" else "R-1": 100})
    service = AssessmentService(repository, Mock())
    with pytest.raises(AssessmentStateError if invalid == "state" else AssessmentInputError):
        service.run_assessment("submission", (context, bidder, verification, rules))
    repository.persist.assert_not_called()
    service.evidence_provider.load.assert_not_called()


@pytest.mark.parametrize("error,status", [(AssessmentNotFoundError("not found"), 404),
    (AssessmentInputError("missing input"), 422), (AssessmentStateError("bad state"), 409),
    (RuntimeError("secret should not escape"), 500)])
def test_assess_error_mapping(error, status):
    service = Mock()
    service.run_assessment.side_effect = error
    app = create_app()
    app.dependency_overrides[get_assessment_service] = lambda: service
    response = TestClient(app).post("/api/v1/submissions/submission/assess")
    assert response.status_code == status
    assert "secret" not in response.text


def test_assess_route_calls_service():
    service = Mock()
    service.run_assessment.return_value = summary()
    app = create_app()
    app.dependency_overrides[get_assessment_service] = lambda: service
    response = TestClient(app).post("/api/v1/submissions/submission/assess")
    assert response.status_code == 200
    service.run_assessment.assert_called_once_with("submission")
