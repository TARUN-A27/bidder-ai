from __future__ import annotations

import re
from decimal import Decimal

from app.schemas.compliance import RequirementEvaluationResult
from app.schemas.scoring import (
    BidAssessmentResult,
    RiskLevel,
    RiskOverrideRule,
    RiskOverrideTrigger,
    ScoringRules,
)


RISK_ORDER: dict[RiskLevel, int] = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


class RiskEvaluationError(Exception):
    """Raised when configured risk cannot be resolved safely."""


class RiskEngine:
    def determine_base_risk(
        self,
        score: Decimal,
        rules: ScoringRules,
    ) -> RiskLevel:
        matching = [
            band.risk_level for band in rules.base_risk_bands if band.contains(score)
        ]
        if len(matching) != 1:
            raise RiskEvaluationError(
                f"Score {score} matched {len(matching)} configured risk bands"
            )
        return matching[0]

    def evaluate_overrides(
        self,
        results: list[RequirementEvaluationResult],
        rules: ScoringRules,
    ) -> list[RiskOverrideTrigger]:
        result_map = {result.requirement_code: result for result in results}
        triggers: list[RiskOverrideTrigger] = []
        for override in rules.risk_overrides:
            trigger = self._evaluate_override(override, result_map, rules)
            if trigger is not None:
                triggers.append(trigger)
        return triggers

    def _evaluate_override(self, override, result_map, rules):
        if override.override_id == "RISK-OVR-001":
            result = result_map.get("LEGAL-DEBAR-001")
            active = bool(result and result.evidence.get("active_debarment") is True)
            if result and result.status == "NON_COMPLIANT" and active:
                return self._trigger(override, ["LEGAL-DEBAR-001"])
            return None

        if override.override_id == "RISK-OVR-002":
            failures = [
                code
                for code in rules.critical_requirement_ids
                if code in result_map
                and result_map[code].status in {"NON_COMPLIANT", "MISSING"}
            ]
            if len(failures) >= 2:
                return self._trigger(override, failures)
            return None

        requirement_codes = re.findall(
            r"\b[A-Z]+(?:-[A-Z]+)*-\d+\b", override.condition
        )
        statuses = set(
            re.findall(
                r"\b(?:COMPLIANT|NON_COMPLIANT|MISSING|NEEDS_REVIEW|NOT_APPLICABLE)\b",
                override.condition,
            )
        )
        if len(requirement_codes) != 1 or not statuses:
            raise RiskEvaluationError(
                f"Cannot interpret condition for {override.override_id}: "
                f"{override.condition}"
            )
        code = requirement_codes[0]
        result = result_map.get(code)
        if result and result.status in statuses:
            return self._trigger(override, [code])
        return None

    @staticmethod
    def _trigger(
        override: RiskOverrideRule,
        requirement_codes: list[str],
    ) -> RiskOverrideTrigger:
        return RiskOverrideTrigger(
            override_id=override.override_id,
            minimum_risk=override.minimum_risk,
            reason=override.condition,
            related_requirement_codes=requirement_codes,
        )

    def resolve_final_risk(
        self,
        base_risk: RiskLevel,
        triggers: list[RiskOverrideTrigger],
        rules: ScoringRules,
    ) -> RiskLevel:
        if rules.risk_resolution != (
            "FINAL_RISK_IS_HIGHER_OF_BASE_SCORE_RISK_AND_OVERRIDE_RISK"
        ):
            raise RiskEvaluationError(
                f"Unsupported risk resolution: {rules.risk_resolution}"
            )
        candidates = [base_risk, *(item.minimum_risk for item in triggers)]
        return max(candidates, key=RISK_ORDER.__getitem__)


class RecommendationResolver:
    def resolve(
        self,
        final_risk: RiskLevel,
        results: list[RequirementEvaluationResult],
        rules: ScoringRules,
    ) -> str:
        if "RECOMMEND" not in rules.decision_policy.ai_may:
            raise RiskEvaluationError(
                "Configured decision policy does not authorize recommendations"
            )
        hard_failures = [
            result
            for result in results
            if result.status in {"NON_COMPLIANT", "MISSING"}
        ]
        reviews = [
            result for result in results if result.status == "NEEDS_REVIEW"
        ]
        if final_risk == "LOW" and not hard_failures and not reviews:
            return "Qualification recommended, subject to Procurement Officer review."
        if final_risk == "CRITICAL":
            return (
                "Strong non-compliance flag; qualification not recommended. "
                "Final decision remains with the Procurement Officer."
            )
        return (
            "Not recommended for unconditional qualification. Refer to "
            "Procurement Officer for clarification/admissibility review."
        )
