from __future__ import annotations

from decimal import Decimal

from app.schemas.compliance import (
    BidderEvidenceBundle,
    RequirementEvaluationResult,
    TenderRequirementContext,
)
from app.schemas.verification_evidence import VerificationEvidenceBundle
from app.services.compliance.base import (
    RequirementEvaluator,
    exact_text_match,
    source_reference,
    status_is,
)


class GstRegistrationEvaluator(RequirementEvaluator):
    requirement_code = "STAT-GST-001"

    def evaluate(self, context, bidder, verification):
        source = verification.gst
        if source is None:
            return self.result(
                "NEEDS_REVIEW",
                "Authoritative GST registration data is unavailable.",
            )
        status = source.status_at_bid_close or source.status
        evidence = {
            "gstin": source.gstin,
            "status_at_bid_close": status,
            "cancellation_date": source.cancellation_date,
        }
        if status_is(status, "ACTIVE"):
            return self.result(
                "COMPLIANT",
                "Authoritative GST registration is active at bid closing.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if status:
            return self.result(
                "NON_COMPLIANT",
                f"Authoritative GST registration is {status} at bid closing.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "NEEDS_REVIEW",
            "GST source exists but has no usable registration state.",
            evidence=evidence,
            source_references=source_reference(source),
        )


class GstFilingEvaluator(RequirementEvaluator):
    requirement_code = "STAT-GST-002"

    def evaluate(self, context, bidder, verification):
        source = verification.gst
        if source is None:
            return self.result("MISSING", "Authoritative GST filing data is absent.")
        evidence = {
            "required_through": context.required_contribution_period,
            "latest_return_period": source.latest_return_period,
            "missing_return_periods": source.missing_return_periods,
        }
        if source.missing_return_periods:
            periods = ", ".join(source.missing_return_periods)
            return self.result(
                "NON_COMPLIANT",
                f"GST returns are explicitly unfiled for: {periods}.",
                evidence=evidence,
                source_references=source_reference(source),
            )

        due_returns = [
            item
            for item in source.returns
            if item.period <= context.required_contribution_period
        ]
        unfiled = [
            item.period
            for item in due_returns
            if not (
                status_is(item.gstr1_status, "FILED")
                and status_is(item.gstr3b_status, "FILED")
            )
        ]
        if unfiled:
            evidence["unfiled_return_records"] = unfiled
            return self.result(
                "NON_COMPLIANT",
                "One or more GST returns due by the cutoff are not filed.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if (
            due_returns
            and source.latest_return_period
            and source.latest_return_period >= context.required_contribution_period
        ):
            return self.result(
                "COMPLIANT",
                "Authoritative GST returns are filed through the required period.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "NEEDS_REVIEW",
            "GST filing records do not establish coverage through the required period.",
            evidence=evidence,
            source_references=source_reference(source),
        )


class PanIdentityEvaluator(RequirementEvaluator):
    requirement_code = "ID-PAN-001"

    def evaluate(self, context, bidder, verification):
        submitted = bidder.pan
        source = verification.pan
        if submitted is None:
            return self.result("MISSING", "Submitted PAN evidence is absent.")
        if source is None:
            return self.result(
                "NEEDS_REVIEW",
                "Authoritative PAN data is unavailable.",
                evidence={"submitted_pan": submitted.fields.pan_reference},
            )
        pan_match = exact_text_match(
            submitted.fields.pan_reference, source.pan_reference
        )
        name_match = exact_text_match(submitted.fields.legal_name, source.legal_name)
        evidence = {
            "submitted_pan": submitted.fields.pan_reference,
            "authoritative_pan": source.pan_reference,
            "submitted_legal_name": submitted.fields.legal_name,
            "authoritative_legal_name": source.legal_name,
            "source_identity_match": source.identity_match,
        }
        if not pan_match or not name_match or status_is(
            source.identity_match, "MATERIAL_MISMATCH", "MISMATCH"
        ):
            return self.result(
                "NON_COMPLIANT",
                "Submitted PAN identity differs from the authoritative record.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if status_is(source.status, "VALID"):
            return self.result(
                "COMPLIANT",
                "Submitted PAN and legal name match the valid authoritative record.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "NEEDS_REVIEW",
            "PAN identity matches, but authoritative validity is unclear.",
            evidence=evidence,
            source_references=source_reference(source),
        )


class UdyamEvaluator(RequirementEvaluator):
    requirement_code = "STAT-UDYAM-001"

    def evaluate(self, context, bidder, verification):
        if not bidder.claims.mse_purchase_preference:
            return self.result(
                "NOT_APPLICABLE",
                "The bidder does not claim an MSE/Udyam benefit.",
            )
        if bidder.udyam is None:
            return self.result("MISSING", "Claimed Udyam evidence is absent.")
        source = verification.udyam
        if source is None:
            return self.result(
                "MISSING", "Claimed Udyam registration has no authoritative record."
            )
        submitted = bidder.udyam.fields
        identity_matches = (
            exact_text_match(submitted.udyam_number, source.udyam_number)
            and exact_text_match(submitted.pan_reference, source.pan_reference)
            and exact_text_match(submitted.enterprise_name, source.enterprise_name)
        )
        evidence = {
            "registration_number": source.udyam_number,
            "status": source.status,
            "relevant_activity": source.relevant_activity,
            "identity_matches": identity_matches,
        }
        if not identity_matches or source.relevant_activity is False:
            return self.result(
                "NON_COMPLIANT",
                "Claimed Udyam record is mismatched or not relevant to the tender.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if status_is(source.status, "VALID", "ACTIVE"):
            return self.result(
                "COMPLIANT",
                "Claimed Udyam registration is valid, matching, and relevant.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if source.status:
            return self.result(
                "NON_COMPLIANT",
                f"Authoritative Udyam state is {source.status}.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "NEEDS_REVIEW",
            "Udyam record exists but its validity is unclear.",
            evidence=evidence,
            source_references=source_reference(source),
        )


class EpfoRegistrationEvaluator(RequirementEvaluator):
    requirement_code = "STAT-EPFO-001"

    def evaluate(self, context, bidder, verification):
        source = verification.epfo
        if source is None:
            return self.result("MISSING", "Authoritative EPFO record is absent.")
        evidence = {
            "establishment_code": source.establishment_code,
            "registration_status": source.registration_status,
            "pan_reference": source.pan_reference,
        }
        identity_matches = exact_text_match(
            source.pan_reference, bidder.pan_reference
        ) and exact_text_match(source.establishment_name, bidder.legal_name)
        if not identity_matches or not status_is(
            source.registration_status, "ACTIVE", "VALID"
        ):
            return self.result(
                "NON_COMPLIANT",
                "Authoritative EPFO registration is inactive, invalid, or identity-mismatched.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "COMPLIANT",
            "Authoritative EPFO registration is active and identity-matched.",
            evidence=evidence,
            source_references=source_reference(source),
        )


class EpfoContributionEvaluator(RequirementEvaluator):
    requirement_code = "STAT-EPFO-002"

    def evaluate(self, context, bidder, verification):
        source = verification.epfo
        if source is None:
            return self.result("MISSING", "Authoritative EPFO contribution data is absent.")
        evidence = {
            "required_period": context.required_contribution_period,
            "compliant_through": source.compliant_through,
            "latest_due_period": source.latest_due_period,
            "payment_status": source.payment_status,
            "payment_date": source.payment_date,
            "outstanding_amount": source.outstanding_amount,
        }
        if (
            status_is(source.contribution_state, "OVERDUE", "DEFAULTING")
            or status_is(source.payment_status, "UNPAID", "OVERDUE")
            or (source.outstanding_amount or Decimal("0")) > 0
        ):
            return self.result(
                "NON_COMPLIANT",
                "Authoritative EPFO facts show an unpaid or outstanding required contribution.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if (
            source.compliant_through
            and source.compliant_through >= context.required_contribution_period
            and source.outstanding_amount == 0
            and source.payment_date is not None
        ):
            return self.result(
                "COMPLIANT",
                "EPFO payment facts cover the required period with no outstanding amount.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "NEEDS_REVIEW",
            "EPFO facts do not establish current payment through the required period.",
            evidence=evidence,
            source_references=source_reference(source),
        )


class EsicEvaluator(RequirementEvaluator):
    requirement_code = "STAT-ESIC-001"

    def evaluate(self, context, bidder, verification):
        source = verification.esic
        if source is None:
            return self.result("MISSING", "Authoritative ESIC data is absent.")
        state = source.status_at_bid_close or source.registration_status
        evidence = {
            "registration_status": source.registration_status,
            "status_at_bid_close": source.status_at_bid_close,
            "contribution_state": source.contribution_state,
            "compliant_through": source.compliant_through,
            "outstanding_amount": source.outstanding_amount,
        }
        if (
            not status_is(state, "ACTIVE", "VALID")
            or status_is(source.contribution_state, "DEFAULTING", "OVERDUE", "UNPAID")
            or (source.outstanding_amount or Decimal("0")) > 0
        ):
            return self.result(
                "NON_COMPLIANT",
                "Authoritative ESIC facts show inactive coverage, default, or an outstanding amount.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if (
            source.compliant_through
            and source.compliant_through >= context.required_contribution_period
            and source.outstanding_amount == 0
            and source.payment_date is not None
        ):
            return self.result(
                "COMPLIANT",
                "ESIC registration is active and payment facts cover the required period.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "NEEDS_REVIEW",
            "ESIC source exists but current contribution standing is unclear.",
            evidence=evidence,
            source_references=source_reference(source),
        )


STATUTORY_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    GstRegistrationEvaluator,
    GstFilingEvaluator,
    PanIdentityEvaluator,
    UdyamEvaluator,
    EpfoRegistrationEvaluator,
    EpfoContributionEvaluator,
    EsicEvaluator,
)
