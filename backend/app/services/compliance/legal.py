from __future__ import annotations

from app.services.compliance.base import RequirementEvaluator, source_reference


class DebarmentEvaluator(RequirementEvaluator):
    requirement_code = "LEGAL-DEBAR-001"

    def evaluate(self, context, bidder, verification):
        source = verification.debarment
        if source is None or source.active is None:
            return self.result(
                "NEEDS_REVIEW",
                "Authoritative debarment status is unavailable.",
                source_references=source_reference(source),
            )
        evidence = {
            "active_debarment": source.active,
            "effective_from": source.effective_from,
            "valid_through": source.valid_through,
            "order_reference": source.order_reference,
        }
        if source.active:
            return self.result(
                "NON_COMPLIANT",
                "Authoritative registry shows an active debarment at the tender cutoff.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "COMPLIANT",
            "Authoritative registry shows no active debarment.",
            evidence=evidence,
            source_references=source_reference(source),
        )


LEGAL_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    DebarmentEvaluator,
)
