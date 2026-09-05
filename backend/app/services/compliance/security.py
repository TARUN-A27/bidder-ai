from __future__ import annotations

from app.services.compliance.base import (
    RequirementEvaluator,
    exact_text_match,
    source_reference,
    status_is,
)


class EmdEvaluator(RequirementEvaluator):
    requirement_code = "SEC-EMD-001"

    def evaluate(self, context, bidder, verification):
        source = verification.emd
        if not bidder.emd_documents:
            return self.result("MISSING", "Submitted EMD payment or exemption evidence is absent.")
        if source is None:
            return self.result(
                "NEEDS_REVIEW",
                "Submitted EMD evidence has no authoritative verification.",
            )

        evidence = {
            "evidence_type": source.evidence_type,
            "amount": source.amount,
            "payment_reference": source.payment_reference,
            "payment_date": source.payment_date,
            "paid_before_bid_deadline": source.paid_before_bid_deadline,
            "exemption_claimed": source.exemption_claimed,
        }
        if source.evidence_type == "PAYMENT":
            valid_payment = bool(
                status_is(source.payment_status, "PAID")
                and source.amount is not None
                and source.amount >= context.emd_amount_inr
                and source.payment_reference
                and source.payment_reference_valid is True
                and source.paid_before_bid_deadline is True
                and source.bid_number_match is True
                and source.bidder_identity_match is True
                and exact_text_match(source.bid_number, context.bid_number)
                and exact_text_match(source.pan_reference, bidder.pan_reference)
            )
            if valid_payment:
                return self.result(
                    "COMPLIANT",
                    "Authoritative evidence confirms timely EMD payment for the required amount.",
                    evidence=evidence,
                    source_references=source_reference(source),
                )
            return self.result(
                "NON_COMPLIANT",
                "EMD payment evidence does not satisfy amount, timing, identity, or reference checks.",
                evidence=evidence,
                source_references=source_reference(source),
            )

        if source.evidence_type == "EXEMPTION":
            submitted_claim = any(
                document.fields.evidence_type == "EXEMPTION_CLAIM"
                and document.fields.exemption_claimed is True
                for document in bidder.emd_documents
            )
            exemption_valid = bool(
                bidder.claims.emd_exemption
                and submitted_claim
                and source.tender_permits_exemption is True
                and source.bidder_identity_match is True
                and source.udyam_valid is True
                and source.nsic_valid is True
                and source.nsic_category_relevant is True
                and verification.udyam is not None
                and verification.nsic is not None
            )
            evidence.update(
                {
                    "submitted_exemption_claim": submitted_claim,
                    "udyam_valid": source.udyam_valid,
                    "nsic_valid": source.nsic_valid,
                    "nsic_category_relevant": source.nsic_category_relevant,
                }
            )
            if exemption_valid:
                return self.result(
                    "COMPLIANT",
                    "Tender-specific EMD exemption facts are verified by Udyam and NSIC sources.",
                    evidence=evidence,
                    source_references=source_reference(source),
                )
            return self.result(
                "NON_COMPLIANT",
                "Claimed EMD exemption does not satisfy the tender-specific verification conditions.",
                evidence=evidence,
                source_references=source_reference(source),
            )

        return self.result(
            "NEEDS_REVIEW",
            "Authoritative EMD evidence type is not recognized.",
            evidence=evidence,
            source_references=source_reference(source),
        )


SECURITY_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (EmdEvaluator,)
