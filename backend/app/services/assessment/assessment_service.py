from datetime import datetime, timezone

from app.schemas.assessment import AssessmentSummaryResponse, ComparisonResponse, PersistedRequirementResult
from app.services.assessment.errors import AssessmentInputError, AssessmentStateError
from app.services.compliance.compliance_engine import ComplianceEngine
from app.services.scoring.scoring_engine import ScoringEngine


class AssessmentPersistenceService:
    def __init__(self, repository):
        self.repository = repository

    def persist(self, summary, verification):
        self.repository.persist(summary, verification)
        return summary


class AssessmentService:
    def __init__(self, repository, evidence_provider):
        self.repository = repository
        self.evidence_provider = evidence_provider

    def run_assessment(self, submission_id, prepared_inputs=None):
        submission = self.repository.submission(submission_id)
        if submission.status not in {"UPLOADED", "SUBMITTED", "ASSESSED", "COMPLETED"}:
            raise AssessmentStateError("Submission is not in an assessable state")
        context, bidder, verification, rules = prepared_inputs or self.evidence_provider.load(submission)
        if (bidder.legal_name != submission.bidder_name or bidder.pan_reference != submission.pan_reference
                or bidder.offered_model != submission.offered_model
                or context.dataset_id != submission.dataset_id or context.bid_number != submission.bid_number
                or verification.bidder_id != bidder.bidder_id or verification.dataset_id != context.dataset_id
                or rules.dataset_id != context.dataset_id):
            raise AssessmentInputError("Assessment inputs do not match the existing submission")
        detail = self.repository.tender(submission.tender_id)
        metadata = {r["requirement_code"]: r for r in detail["requirements"]}
        if set(metadata) != set(context.requirement_codes) or set(metadata) != set(rules.requirement_weights):
            raise AssessmentInputError("Database and prototype tender requirements differ")
        if any(float(rules.requirement_weights[code]) != float(row["weight"]) for code, row in metadata.items()):
            raise AssessmentInputError("Database and prototype requirement weights differ")
        results = ComplianceEngine().evaluate(context, bidder, verification)
        assessment = ScoringEngine().assess(results, rules)
        scores = {r.requirement_code: r for r in assessment.requirement_scores}
        summary = AssessmentSummaryResponse(
            **assessment.model_dump(), submission_id=submission_id, bidder_id=submission.bidder_id,
            bidder_name=submission.bidder_name, tender_id=submission.tender_id,
            assessed_at=datetime.now(timezone.utc), requirement_results=[PersistedRequirementResult(
                **result.model_dump(), title=metadata[result.requirement_code]["title"],
                configured_weight=scores[result.requirement_code].configured_weight,
                awarded_points=scores[result.requirement_code].awarded_points) for result in results])
        return AssessmentPersistenceService(self.repository).persist(summary, verification)

    def comparison(self, tender_id):
        bidders = []
        for submission in self.repository.submissions(tender_id):
            if not submission["assessment_available"]:
                continue
            assessment = self.repository.assessment(submission["submission_id"])
            counts = {status: sum(r.status == status for r in assessment.requirement_results)
                      for status in ("NON_COMPLIANT", "MISSING", "NEEDS_REVIEW")}
            bidders.append(dict(submission_id=assessment.submission_id, bidder_name=assessment.bidder_name,
                                score=assessment.score, final_risk=assessment.final_risk,
                                recommendation=assessment.recommendation,
                                non_compliant_count=counts["NON_COMPLIANT"], missing_count=counts["MISSING"],
                                needs_review_count=counts["NEEDS_REVIEW"]))
        return ComparisonResponse(tender_id=tender_id, bidders=bidders)
