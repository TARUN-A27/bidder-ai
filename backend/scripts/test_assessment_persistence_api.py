from pathlib import Path
import json
import logging
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.core.config import get_settings
from app.db.oracle import database_is_healthy
from app.main import create_app
from app.api.v1.assessments import get_assessment_service
from app.repositories.assessment_repository import AssessmentRepository
from app.services.assessment.assessment_service import AssessmentService
from app.services.assessment.prototype_evidence import PrototypeEvidenceProvider
from seed_test_bidder_submissions import ensure_prototype_submissions


def main():
    logging.getLogger("azure").setLevel(logging.WARNING)
    with TestClient(create_app()) as client:
        assert database_is_healthy()
        settings = get_settings()
        identities = ensure_prototype_submissions(settings)
        assert ensure_prototype_submissions(settings) == identities
        repository = AssessmentRepository()
        provider = PrototypeEvidenceProvider(settings)
        service = AssessmentService(repository, provider)
        expected = {"BIDDER_A": (100.0, "LOW", []), "BIDDER_B": (80.5, "HIGH", ["RISK-OVR-005"]),
                    "BIDDER_C": (34.0, "CRITICAL", [f"RISK-OVR-{i:03}" for i in range(1, 8)])}
        for label, submission_id, tender_id in identities:
            print(f"Assessing {label}", flush=True)
            inputs = provider.load(repository.submission(submission_id))
            result = service.run_assessment(submission_id, inputs)
            if label == "BIDDER_A":
                # Exercise the real POST orchestration/persistence using already normalized evidence.
                class PreparedEvidence:
                    def load(self, submission):
                        assert submission.submission_id == submission_id
                        return inputs

                client.app.dependency_overrides[get_assessment_service] = lambda: AssessmentService(repository, PreparedEvidence())
                try:
                    response = client.post(f"/api/v1/submissions/{submission_id}/assess")
                    assert response.status_code == 200, response.text
                    result = type(result).model_validate(response.json())
                finally:
                    client.app.dependency_overrides.pop(get_assessment_service)
            persisted = repository.assessment(submission_id)
            assert persisted.model_dump(mode="json") == result.model_dump(mode="json")
            score, risk, overrides = expected[label]
            assert (persisted.score, persisted.final_risk) == (score, risk)
            assert [r.override_id for r in persisted.triggered_risk_overrides] == overrides
            rows = repository.query("""SELECT rr.status,rr.awarded_points,rr.ai_explanation,tr.requirement_code
                FROM requirement_results rr JOIN tender_requirements tr ON tr.id=rr.requirement_id
                WHERE rr.submission_id=:id""", id=submission_id)
            assert len(rows) == len({r["requirement_code"] for r in rows}) == 16
            for row in rows:
                stored = json.loads(row["ai_explanation"])
                assert stored["status"] == row["status"]
                assert stored["awarded_points"] == row["awarded_points"]
            assert repository.query("SELECT COUNT(*) n FROM risk_assessments WHERE submission_id=:id", id=submission_id)[0]["n"] == 1
            assert repository.query("SELECT COUNT(*) n FROM verification_checks WHERE submission_id=:id", id=submission_id)[0]["n"] == 14
            for path in (f"/api/v1/submissions/{submission_id}", f"/api/v1/submissions/{submission_id}/assessment",
                         f"/api/v1/submissions/{submission_id}/requirement-results"):
                response = client.get(path)
                assert response.status_code == 200, response.text
            print(label, persisted.score, persisted.final_risk, overrides, "16 current rows", flush=True)
        tender_id = identities[0][2]
        for path in ("/api/v1/tenders", f"/api/v1/tenders/{tender_id}", f"/api/v1/tenders/{tender_id}/submissions"):
            response = client.get(path)
            assert response.status_code == 200, response.text
        detail = client.get(f"/api/v1/tenders/{tender_id}").json()
        assert len(detail["requirements"]) == 16 and len(detail["technical_requirements"]) == 14
        comparison = client.get(f"/api/v1/tenders/{tender_id}/comparison")
        assert comparison.status_code == 200, comparison.text
        assert {b["submission_id"] for b in comparison.json()["bidders"]} >= {r[1] for r in identities}
        assert client.get("/api/v1/submissions/absent/assessment").status_code == 404
        assert client.post("/api/v1/submissions/absent/assess").status_code == 404
        print("PASS: Oracle persistence, A reassessment, and assessment read APIs")


if __name__ == "__main__":
    main()
