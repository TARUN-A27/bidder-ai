from __future__ import annotations

from app.services.compliance.base import (
    RequirementEvaluator,
    exact_text_match,
    source_reference,
)


class LocalContentEvaluator(RequirementEvaluator):
    requirement_code = "MII-LC-001"

    def evaluate(self, context, bidder, verification):
        if bidder.local_content is None:
            return self.result("MISSING", "Submitted local-content evidence is absent.")
        source = verification.local_content
        if source is None:
            return self.result(
                "NEEDS_REVIEW",
                "Submitted local-content evidence has no authoritative verification.",
            )
        verified = source.verified_local_content_percentage
        evidence = {
            "declared_percentage": (
                bidder.local_content.fields.local_content_percentage
            ),
            "authoritative_declared_percentage": (
                source.declared_local_content_percentage
            ),
            "verified_percentage": verified,
            "required_percentage": context.minimum_local_content_percent,
            "entity_matches": exact_text_match(
                source.entity_name, bidder.legal_name
            ),
            "model_matches": exact_text_match(
                source.offered_model, bidder.offered_model
            ),
        }
        if verified is None:
            return self.result(
                "NEEDS_REVIEW",
                "Authoritative local-content percentage is unavailable.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if not evidence["entity_matches"] or not evidence["model_matches"]:
            return self.result(
                "NON_COMPLIANT",
                "Local-content verification does not match the bidder or offered model.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if verified < context.minimum_local_content_percent:
            return self.result(
                "NON_COMPLIANT",
                "Verified local content is below the configured tender threshold.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "COMPLIANT",
            "Verified local content meets the configured tender threshold.",
            evidence=evidence,
            source_references=source_reference(source),
        )


LOCAL_CONTENT_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    LocalContentEvaluator,
)
