from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.compliance import RequirementEvaluationResult
from app.schemas.scoring import (
    BidAssessmentResult,
    RequirementScoreDetail,
    ScoringRules,
)
from app.services.scoring.risk_engine import (
    RecommendationResolver,
    RiskEngine,
)


class ScoringEvaluationError(Exception):
    """Raised when requirement results cannot be scored safely."""


class ScoringEngine:
    def __init__(self) -> None:
        self._risk_engine = RiskEngine()
        self._recommendation_resolver = RecommendationResolver()

    def assess(
        self,
        results: list[RequirementEvaluationResult],
        rules: ScoringRules,
    ) -> BidAssessmentResult:
        self._validate_results(results, rules)
        details: list[RequirementScoreDetail] = []
        numerator = Decimal("0")
        denominator = Decimal("0")

        for result in results:
            weight = rules.requirement_weights[result.requirement_code]
            credit = rules.status_credit[result.status]
            applicable = result.status != "NOT_APPLICABLE"
            awarded = Decimal("0")
            if applicable:
                if credit is None:
                    raise ScoringEvaluationError(
                        f"Applicable status {result.status} has null credit"
                    )
                denominator += weight
                awarded = weight * credit
                numerator += awarded
            details.append(
                RequirementScoreDetail(
                    requirement_code=result.requirement_code,
                    status=result.status,
                    configured_weight=float(weight),
                    status_credit=float(credit) if credit is not None else None,
                    applicable=applicable,
                    awarded_points=float(awarded),
                )
            )

        if denominator <= 0:
            raise ScoringEvaluationError(
                "No applicable requirement weight remains after exclusions"
            )
        scale_span = rules.score_scale.maximum - rules.score_scale.minimum
        raw_score = rules.score_scale.minimum + scale_span * numerator / denominator
        quantum = Decimal("1").scaleb(-rules.rounding.decimal_places)
        score = raw_score.quantize(quantum, rounding=ROUND_HALF_UP)

        base_risk = self._risk_engine.determine_base_risk(score, rules)
        triggers = self._risk_engine.evaluate_overrides(results, rules)
        final_risk = self._risk_engine.resolve_final_risk(
            base_risk, triggers, rules
        )
        recommendation = self._recommendation_resolver.resolve(
            final_risk, results, rules
        )
        return BidAssessmentResult(
            score=float(score),
            base_risk=base_risk,
            triggered_risk_overrides=triggers,
            final_risk=final_risk,
            recommendation=recommendation,
            requirement_scores=details,
            configured_applicable_weight=float(denominator),
            configured_total_weight=float(rules.total_configured_weight),
            final_decision_authority=(
                rules.decision_policy.final_decision_authority
            ),
        )

    @staticmethod
    def _validate_results(
        results: list[RequirementEvaluationResult],
        rules: ScoringRules,
    ) -> None:
        codes = [result.requirement_code for result in results]
        if len(codes) != len(set(codes)):
            raise ScoringEvaluationError("Duplicate requirement result codes")
        configured = set(rules.requirement_weights)
        evaluated = set(codes)
        missing = sorted(configured - evaluated)
        unexpected = sorted(evaluated - configured)
        if missing or unexpected:
            details = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if unexpected:
                details.append(f"unexpected: {', '.join(unexpected)}")
            raise ScoringEvaluationError(
                f"Result/configuration mismatch ({'; '.join(details)})"
            )
        invalid_statuses = sorted(
            {
                result.status
                for result in results
                if result.status not in rules.status_credit
            }
        )
        if invalid_statuses:
            raise ScoringEvaluationError(
                f"Unconfigured statuses: {', '.join(invalid_statuses)}"
            )
