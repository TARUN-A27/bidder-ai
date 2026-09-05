from __future__ import annotations

import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.core.config import get_settings
from app.schemas.compliance import RequirementEvaluationResult, TenderRequirementContext
from app.schemas.scoring import BidAssessmentResult, ScoringRules
from app.services.compliance.base import ComplianceEvaluationError
from app.services.compliance.compliance_engine import ComplianceEngine
from app.services.document_processing.azure_document_intelligence import (
    AzureDocumentIntelligenceService,
    DocumentExtractionError,
)
from app.services.document_processing.document_normalizer import DocumentNormalizer
from app.services.document_processing.normalizers.base import (
    DocumentNormalizationError,
)
from app.services.scoring.config_loader import (
    ScoringConfigLoader,
    ScoringConfigurationError,
)
from app.services.scoring.risk_engine import RiskEvaluationError
from app.services.scoring.scoring_engine import (
    ScoringEngine,
    ScoringEvaluationError,
)
from app.services.verification.mock_verification_loader import (
    MockVerificationError,
    MockVerificationLoader,
)
from test_compliance_engine import (
    BIDDER_DIRECTORIES,
    CONFIG_PATH,
    build_bidder_evidence,
    load_json,
    validate_result_set,
)


SCORING_CONFIG_PATH = (
    Path("/home/tarun/TARUN/projects/test-sih-docs")
    / "config"
    / "scoring_rules.json"
)

EXPECTED_SUMMARIES = {
    "BIDDER_A": (100.0, "LOW", []),
    "BIDDER_B": (80.5, "HIGH", ["RISK-OVR-005"]),
    "BIDDER_C": (
        34.0,
        "CRITICAL",
        [
            "RISK-OVR-001",
            "RISK-OVR-002",
            "RISK-OVR-003",
            "RISK-OVR-004",
            "RISK-OVR-005",
            "RISK-OVR-006",
            "RISK-OVR-007",
        ],
    ),
}


def test_not_applicable_normalization(
    scoring_engine: ScoringEngine,
    rules: ScoringRules,
) -> None:
    results = [
        RequirementEvaluationResult(
            requirement_code=code,
            status=("NOT_APPLICABLE" if code == "STAT-UDYAM-001" else "COMPLIANT"),
            reason="Focused scoring behavior test.",
        )
        for code in rules.requirement_weights
    ]
    assessment = scoring_engine.assess(results, rules)
    udyam = next(
        item
        for item in assessment.requirement_scores
        if item.requirement_code == "STAT-UDYAM-001"
    )
    expected_denominator = float(
        rules.total_configured_weight
        - rules.requirement_weights["STAT-UDYAM-001"]
    )
    if assessment.score != 100.0:
        raise AssertionError(
            f"NOT_APPLICABLE normalization produced {assessment.score}, expected 100.0"
        )
    if assessment.configured_applicable_weight != expected_denominator:
        raise AssertionError("NOT_APPLICABLE weight was not excluded from denominator")
    if udyam.applicable or udyam.status_credit is not None or udyam.awarded_points != 0:
        raise AssertionError("NOT_APPLICABLE score detail is incorrect")


def validate_assessment(
    bidder_id: str,
    assessment: BidAssessmentResult,
) -> None:
    score, final_risk, override_ids = EXPECTED_SUMMARIES[bidder_id]
    actual_ids = [
        item.override_id for item in assessment.triggered_risk_overrides
    ]
    if assessment.score != score:
        raise AssertionError(
            f"{bidder_id}: expected score {score}, received {assessment.score}"
        )
    if assessment.final_risk != final_risk:
        raise AssertionError(
            f"{bidder_id}: expected final risk {final_risk}, "
            f"received {assessment.final_risk}"
        )
    if actual_ids != override_ids:
        raise AssertionError(
            f"{bidder_id}: expected overrides {override_ids}, received {actual_ids}"
        )
    if len(assessment.requirement_scores) != 16:
        raise AssertionError(f"{bidder_id}: expected 16 requirement score details")
    if bidder_id == "BIDDER_B":
        details = {
            item.requirement_code: item for item in assessment.requirement_scores
        }
        expected_points = {
            "STAT-EPFO-002": 0.0,
            "OEM-AUTH-001": 0.0,
            "TECH-SPEC-001": 5.0,
            "DOC-INTEGRITY-001": 1.5,
        }
        for code, points in expected_points.items():
            if details[code].awarded_points != points:
                raise AssertionError(
                    f"BIDDER_B: {code} awarded {details[code].awarded_points}, "
                    f"expected {points}"
                )


def compare_assessment_with_expected_fixture(
    bidder_directory: Path,
    assessment: BidAssessmentResult,
) -> None:
    """Regression-only comparison after independent status/score/risk calculation."""
    expected = load_json(bidder_directory / "expected_result.json")
    comparisons = {
        "score": (assessment.score, expected["compliance_score"]),
        "base_risk": (assessment.base_risk, expected["base_risk"]),
        "final_risk": (assessment.final_risk, expected["final_risk_level"]),
        "recommendation": (
            assessment.recommendation,
            expected["ai_recommendation"],
        ),
        "final_decision_authority": (
            assessment.final_decision_authority,
            expected["final_decision_authority"],
        ),
    }
    for label, (actual, wanted) in comparisons.items():
        if actual != wanted:
            raise AssertionError(
                f"{bidder_directory.name}: {label} expected {wanted!r}, "
                f"received {actual!r}"
            )
    actual_overrides = [
        item.override_id for item in assessment.triggered_risk_overrides
    ]
    expected_overrides = [
        item["override_id"] for item in expected["triggered_risk_overrides"]
    ]
    if actual_overrides != expected_overrides:
        raise AssertionError(
            f"{bidder_directory.name}: override IDs expected "
            f"{expected_overrides}, received {actual_overrides}"
        )
    expected_points = {
        item["requirement_id"]: float(item["awarded_points"])
        for item in expected["requirement_results"]
    }
    actual_points = {
        item.requirement_code: item.awarded_points
        for item in assessment.requirement_scores
    }
    if actual_points != expected_points:
        raise AssertionError(
            f"{bidder_directory.name}: requirement awarded-point mismatch"
        )


def print_assessment(
    bidder_id: str,
    assessment: BidAssessmentResult,
) -> None:
    print(f"\n{bidder_id}")
    print(f"Score: {assessment.score:.1f}")
    print(f"Base risk: {assessment.base_risk}")
    print("Triggered overrides:")
    if assessment.triggered_risk_overrides:
        for trigger in assessment.triggered_risk_overrides:
            print(f"- {trigger.override_id}: {trigger.minimum_risk}")
    else:
        print("- none")
    print(f"Final risk: {assessment.final_risk}")
    print(f"Recommendation: {assessment.recommendation}")


def main() -> int:
    try:
        tender_context = TenderRequirementContext.from_config(
            load_json(CONFIG_PATH)
        )
        scoring_rules = ScoringConfigLoader().load(SCORING_CONFIG_PATH)
        if tender_context.dataset_id != scoring_rules.dataset_id:
            raise AssertionError("Tender and scoring configuration datasets differ")

        compliance_engine = ComplianceEngine()
        scoring_engine = ScoringEngine()
        verification_loader = MockVerificationLoader()
        normalizer = DocumentNormalizer()
        test_not_applicable_normalization(scoring_engine, scoring_rules)

        settings = get_settings()
        with AzureDocumentIntelligenceService(settings) as extraction_service:
            for bidder_directory in BIDDER_DIRECTORIES:
                bidder = build_bidder_evidence(
                    bidder_directory, extraction_service, normalizer
                )
                verification = verification_loader.load(
                    bidder_directory / "mock_portal_data.json"
                )
                compliance_results = compliance_engine.evaluate(
                    tender_context, bidder, verification
                )
                validate_result_set(tender_context, compliance_results)
                assessment = scoring_engine.assess(
                    compliance_results, scoring_rules
                )
                validate_assessment(bidder.bidder_id, assessment)
                print_assessment(bidder.bidder_id, assessment)
                compare_assessment_with_expected_fixture(
                    bidder_directory, assessment
                )
    except (
        AssertionError,
        ComplianceEvaluationError,
        DocumentExtractionError,
        DocumentNormalizationError,
        MockVerificationError,
        OSError,
        RiskEvaluationError,
        ScoringConfigurationError,
        ScoringEvaluationError,
        ValueError,
    ) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nPASS: all scoring, risk, override, and fixture assertions passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
