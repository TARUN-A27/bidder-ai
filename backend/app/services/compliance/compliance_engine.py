from __future__ import annotations

from app.schemas.compliance import (
    BidderEvidenceBundle,
    RequirementEvaluationResult,
    TenderRequirementContext,
)
from app.schemas.verification_evidence import VerificationEvidenceBundle
from app.services.compliance.base import (
    ComplianceEvaluationError,
    RequirementEvaluator,
)
from app.services.compliance.document_integrity import (
    DOCUMENT_INTEGRITY_EVALUATORS,
)
from app.services.compliance.experience import EXPERIENCE_EVALUATORS
from app.services.compliance.financial import FINANCIAL_EVALUATORS
from app.services.compliance.legal import LEGAL_EVALUATORS
from app.services.compliance.local_content import LOCAL_CONTENT_EVALUATORS
from app.services.compliance.oem import OEM_EVALUATORS
from app.services.compliance.security import SECURITY_EVALUATORS
from app.services.compliance.statutory import STATUTORY_EVALUATORS
from app.services.compliance.technical import TECHNICAL_EVALUATORS


DEFAULT_EVALUATOR_TYPES: tuple[type[RequirementEvaluator], ...] = (
    *STATUTORY_EVALUATORS,
    *FINANCIAL_EVALUATORS,
    *EXPERIENCE_EVALUATORS,
    *OEM_EVALUATORS,
    *LOCAL_CONTENT_EVALUATORS,
    *LEGAL_EVALUATORS,
    *TECHNICAL_EVALUATORS,
    *SECURITY_EVALUATORS,
    *DOCUMENT_INTEGRITY_EVALUATORS,
)


class ComplianceEngine:
    """Evaluate configured tender requirements without scoring or persistence."""

    def __init__(
        self,
        evaluator_types: tuple[type[RequirementEvaluator], ...] = (
            DEFAULT_EVALUATOR_TYPES
        ),
    ) -> None:
        evaluators = [evaluator_type() for evaluator_type in evaluator_types]
        codes = [evaluator.requirement_code for evaluator in evaluators]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise ComplianceEvaluationError(
                f"Duplicate evaluator codes: {', '.join(duplicates)}"
            )
        self._evaluators = {
            evaluator.requirement_code: evaluator for evaluator in evaluators
        }

    def evaluate(
        self,
        context: TenderRequirementContext,
        bidder: BidderEvidenceBundle,
        verification: VerificationEvidenceBundle,
    ) -> list[RequirementEvaluationResult]:
        if bidder.bidder_id != verification.bidder_id:
            raise ComplianceEvaluationError(
                "Bidder evidence and verification evidence identify different bidders"
            )
        if context.dataset_id != verification.dataset_id:
            raise ComplianceEvaluationError(
                "Tender and verification evidence identify different datasets"
            )

        missing_evaluators = [
            code for code in context.requirement_codes if code not in self._evaluators
        ]
        unexpected_evaluators = [
            code for code in self._evaluators if code not in context.requirement_codes
        ]
        if missing_evaluators or unexpected_evaluators:
            details = []
            if missing_evaluators:
                details.append(f"missing: {', '.join(missing_evaluators)}")
            if unexpected_evaluators:
                details.append(f"unconfigured: {', '.join(unexpected_evaluators)}")
            raise ComplianceEvaluationError(
                f"Evaluator/configuration mismatch ({'; '.join(details)})"
            )

        results: list[RequirementEvaluationResult] = []
        for code in context.requirement_codes:
            evaluator = self._evaluators[code]
            try:
                result = evaluator.evaluate(context, bidder, verification)
            except ComplianceEvaluationError:
                raise
            except Exception as exc:
                raise ComplianceEvaluationError(
                    f"Evaluator {code} failed: {exc}"
                ) from exc
            if result.requirement_code != code:
                raise ComplianceEvaluationError(
                    f"Evaluator {code} returned result for {result.requirement_code}"
                )
            if result.status not in context.allowed_statuses:
                raise ComplianceEvaluationError(
                    f"Evaluator {code} returned unsupported status {result.status}"
                )
            results.append(result)
        return results
