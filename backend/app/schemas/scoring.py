from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.compliance import ComplianceStatus


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

EXPECTED_STATUSES = {
    "COMPLIANT",
    "NON_COMPLIANT",
    "MISSING",
    "NEEDS_REVIEW",
    "NOT_APPLICABLE",
}
EXPECTED_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
EXPECTED_OVERRIDE_IDS = {
    "RISK-OVR-001",
    "RISK-OVR-002",
    "RISK-OVR-003",
    "RISK-OVR-004",
    "RISK-OVR-005",
    "RISK-OVR-006",
    "RISK-OVR-007",
}


class ScoreScale(BaseModel):
    minimum: Decimal
    maximum: Decimal

    @model_validator(mode="after")
    def validate_bounds(self) -> "ScoreScale":
        if self.maximum <= self.minimum:
            raise ValueError("score_scale.maximum must exceed minimum")
        return self


class ScoreRounding(BaseModel):
    decimal_places: int
    method: str

    @model_validator(mode="after")
    def validate_rounding(self) -> "ScoreRounding":
        if self.decimal_places < 0:
            raise ValueError("rounding.decimal_places must be non-negative")
        if self.method != "ROUND_HALF_UP":
            raise ValueError(f"Unsupported rounding method: {self.method}")
        return self


class BaseRiskBand(BaseModel):
    risk_level: RiskLevel
    minimum_inclusive: Decimal | None = None
    minimum_exclusive: Decimal | None = None
    maximum_inclusive: Decimal | None = None
    maximum_exclusive: Decimal | None = None

    def contains(self, score: Decimal) -> bool:
        checks = (
            self.minimum_inclusive is None or score >= self.minimum_inclusive,
            self.minimum_exclusive is None or score > self.minimum_exclusive,
            self.maximum_inclusive is None or score <= self.maximum_inclusive,
            self.maximum_exclusive is None or score < self.maximum_exclusive,
        )
        return all(checks)


class RiskOverrideRule(BaseModel):
    override_id: str
    condition: str
    minimum_risk: RiskLevel


class DecisionPolicy(BaseModel):
    ai_role: str
    ai_may: list[str]
    ai_may_not: list[str]
    final_decision_authority: str


class ScoringRules(BaseModel):
    dataset_id: str
    score_scale: ScoreScale
    total_configured_weight: Decimal
    status_credit: dict[ComplianceStatus, Decimal | None]
    not_applicable_handling: str
    score_formula: str
    rounding: ScoreRounding
    base_risk_bands: list[BaseRiskBand]
    risk_overrides: list[RiskOverrideRule]
    specific_status_rules: list[dict[str, object]] = Field(default_factory=list)
    critical_requirement_ids: list[str]
    requirement_weights: dict[str, Decimal]
    risk_resolution: str
    decision_policy: DecisionPolicy

    @model_validator(mode="after")
    def validate_complete_rules(self) -> "ScoringRules":
        if set(self.status_credit) != EXPECTED_STATUSES:
            raise ValueError("status_credit must configure all allowed statuses")
        if self.status_credit["NOT_APPLICABLE"] is not None:
            raise ValueError("NOT_APPLICABLE credit must be null when excluded")
        if self.not_applicable_handling != (
            "EXCLUDE_FROM_DENOMINATOR_AND_NORMALIZE_TO_100"
        ):
            raise ValueError(
                "Unsupported not_applicable_handling: "
                f"{self.not_applicable_handling}"
            )
        if not self.score_formula.strip():
            raise ValueError("score_formula is required")
        if any(weight <= 0 for weight in self.requirement_weights.values()):
            raise ValueError("Every configured requirement weight must be positive")
        if sum(self.requirement_weights.values()) != self.total_configured_weight:
            raise ValueError("Requirement weights do not equal total_configured_weight")
        if not set(self.critical_requirement_ids) <= set(self.requirement_weights):
            raise ValueError("critical_requirement_ids contains an unknown requirement")
        override_ids = [item.override_id for item in self.risk_overrides]
        if len(override_ids) != len(set(override_ids)):
            raise ValueError("Duplicate risk override IDs")
        if set(override_ids) != EXPECTED_OVERRIDE_IDS:
            raise ValueError("Configured risk override IDs are incomplete or unexpected")
        if {item.risk_level for item in self.base_risk_bands} != EXPECTED_RISK_LEVELS:
            raise ValueError("Base risk bands must configure all risk levels")
        if self.risk_resolution != (
            "FINAL_RISK_IS_HIGHER_OF_BASE_SCORE_RISK_AND_OVERRIDE_RISK"
        ):
            raise ValueError(f"Unsupported risk_resolution: {self.risk_resolution}")
        if "RECOMMEND" not in self.decision_policy.ai_may:
            raise ValueError("decision_policy does not authorize an AI recommendation")
        if not self.decision_policy.final_decision_authority:
            raise ValueError("decision_policy.final_decision_authority is required")
        return self


class RequirementScoreDetail(BaseModel):
    requirement_code: str
    status: ComplianceStatus
    configured_weight: float
    status_credit: float | None
    applicable: bool
    awarded_points: float


class RiskOverrideTrigger(BaseModel):
    override_id: str
    minimum_risk: RiskLevel
    reason: str
    related_requirement_codes: list[str] = Field(default_factory=list)


class BidAssessmentResult(BaseModel):
    score: float
    base_risk: RiskLevel
    triggered_risk_overrides: list[RiskOverrideTrigger]
    final_risk: RiskLevel
    recommendation: str
    requirement_scores: list[RequirementScoreDetail]
    configured_applicable_weight: float
    configured_total_weight: float
    final_decision_authority: str
