from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.compliance import (
    BidderEvidenceBundle,
    ComplianceStatus,
    RequirementEvaluationResult,
    TenderRequirementContext,
)
from app.schemas.verification_evidence import VerificationEvidenceBundle


class ComplianceEvaluationError(Exception):
    """Raised when a requirement cannot be evaluated safely."""


class RequirementEvaluator(ABC):
    requirement_code: str

    @abstractmethod
    def evaluate(
        self,
        context: TenderRequirementContext,
        bidder: BidderEvidenceBundle,
        verification: VerificationEvidenceBundle,
    ) -> RequirementEvaluationResult:
        """Evaluate one configured tender requirement."""

    def result(
        self,
        status: ComplianceStatus,
        reason: str,
        *,
        evidence: dict[str, Any] | None = None,
        source_references: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> RequirementEvaluationResult:
        return RequirementEvaluationResult(
            requirement_code=self.requirement_code,
            status=status,
            reason=reason,
            requires_human_review=status == "NEEDS_REVIEW",
            evidence=evidence or {},
            source_references=source_references or [],
            warnings=warnings or [],
        )


def canonical_identity(value: str | None) -> str | None:
    if value is None:
        return None
    token = re.sub(r"[^a-z0-9]+", "", value.casefold())
    return token or None


def exact_text_match(left: str | None, right: str | None) -> bool:
    return bool(
        canonical_identity(left)
        and canonical_identity(left) == canonical_identity(right)
    )


def source_reference(source: Any | None) -> list[str]:
    if source is None:
        return []
    system = getattr(source, "source_system", None)
    return [system] if isinstance(system, str) else []


def status_is(value: str | None, *states: str) -> bool:
    return bool(value and value.upper() in {item.upper() for item in states})
