from __future__ import annotations

from app.services.compliance.base import (
    RequirementEvaluator,
    exact_text_match,
    source_reference,
    status_is,
)


class OemAuthorizationEvaluator(RequirementEvaluator):
    requirement_code = "OEM-AUTH-001"

    def evaluate(self, context, bidder, verification):
        source = verification.oem_authorization
        if bidder.oem_authorization is None:
            return self.result(
                "MISSING",
                "Mandatory submitted OEM authorization is absent.",
                evidence={
                    "authoritative_document_present": (
                        source.document_present if source else None
                    )
                },
                source_references=source_reference(source),
            )
        if source is None:
            return self.result(
                "NEEDS_REVIEW",
                "Submitted OEM authorization has no authoritative registry record.",
            )
        submitted = bidder.oem_authorization.fields
        evidence = {
            "authorization_number": source.authorization_number,
            "authorized_bidder": source.authorized_bidder,
            "bidder_pan": source.bidder_pan,
            "bid_number": source.bid_number,
            "offered_model": source.offered_model,
            "valid_through": source.valid_through,
            "required_through": context.oem_authorization_required_through,
        }
        if source.document_present is False or not source.authorization_number:
            return self.result(
                "MISSING",
                "Authoritative source confirms that OEM authorization is absent.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        identity_and_scope_match = all(
            (
                exact_text_match(source.authorized_bidder, bidder.legal_name),
                exact_text_match(source.bidder_pan, bidder.pan_reference),
                exact_text_match(source.bid_number, context.bid_number),
                exact_text_match(source.offered_model, bidder.offered_model),
                exact_text_match(
                    submitted.authorization_number, source.authorization_number
                ),
                exact_text_match(submitted.authorized_bidder, source.authorized_bidder),
                exact_text_match(submitted.bid_number, source.bid_number),
            )
        )
        if not identity_and_scope_match:
            return self.result(
                "NON_COMPLIANT",
                "OEM authorization does not exactly match the bidder, bid, model, or registry record.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if not status_is(source.status_at_bid_close or source.status, "VALID", "ACTIVE"):
            return self.result(
                "NON_COMPLIANT",
                "OEM authorization is not valid at bid closing.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if source.valid_through is None:
            return self.result(
                "NEEDS_REVIEW",
                "OEM authorization has no usable validity end date.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if source.valid_through < context.oem_authorization_required_through:
            return self.result(
                "NON_COMPLIANT",
                "OEM authorization expires before the tender-required date.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "COMPLIANT",
            "OEM authorization matches the bidder, bid, and model and covers the required validity period.",
            evidence=evidence,
            source_references=source_reference(source),
        )


OEM_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    OemAuthorizationEvaluator,
)
