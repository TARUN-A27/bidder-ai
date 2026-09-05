from contextlib import contextmanager
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.assessments import get_assessment_service
from app.main import create_app
from app.repositories.assessment_repository import AssessmentRepository
from app.schemas.assessment import AssessmentSummaryResponse, PersistedRequirementResult
from app.services.assessment.errors import AssessmentInputError, AssessmentNotFoundError, AssessmentStateError
from app.services.assessment.assessment_service import AssessmentService
from app.services.assessment.prototype_evidence import PrototypeEvidenceProvider
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
    provider = PrototypeEvidenceProvider(SimpleNamespace(prototype_dataset_root=tmp_path))
    with pytest.raises(AssessmentInputError, match="No unique prototype evidence"):
        provider.load(Mock())


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
