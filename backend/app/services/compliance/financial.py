from __future__ import annotations

from app.services.compliance.base import (
    RequirementEvaluator,
    exact_text_match,
    source_reference,
    status_is,
)


class TurnoverEvaluator(RequirementEvaluator):
    requirement_code = "FIN-TURN-001"

    def evaluate(self, context, bidder, verification):
        turnover = bidder.turnover
        audited = bidder.audited_financials
        if turnover is None and audited is None:
            return self.result("MISSING", "Normalized financial turnover evidence is absent.")

        certificate_average = (
            turnover.fields.average_turnover if turnover is not None else None
        )
        audited_average = (
            audited.fields.average_turnover if audited is not None else None
        )
        average = certificate_average or audited_average
        evidence = {
            "certificate_average_turnover": certificate_average,
            "audited_average_turnover": audited_average,
            "required_average_turnover": context.turnover_threshold_inr,
            "startup_relaxation_claimed": (
                bidder.claims.startup_turnover_relaxation
            ),
        }
        if average is None:
            return self.result(
                "MISSING",
                "Financial documents do not contain a usable average turnover.",
                evidence=evidence,
            )
        if (
            certificate_average is not None
            and audited_average is not None
            and certificate_average != audited_average
        ):
            return self.result(
                "NEEDS_REVIEW",
                "Turnover certificate and audited extracts report different averages.",
                evidence=evidence,
            )
        if average >= context.turnover_threshold_inr:
            return self.result(
                "COMPLIANT",
                "Average turnover meets the configured tender threshold.",
                evidence=evidence,
            )

        if not bidder.claims.startup_turnover_relaxation:
            return self.result(
                "NON_COMPLIANT",
                "Average turnover is below the tender threshold and no relaxation is claimed.",
                evidence=evidence,
            )

        dpiit = verification.dpiit
        has_certificate = any(
            "dpiit" in document.file_name.casefold()
            for document in bidder.manifest.documents
        )
        relaxation_valid = bool(
            dpiit
            and context.startup_relaxation_permitted
            and self.requirement_code in context.startup_relaxed_requirement_ids
            and dpiit.claim_submitted is True
            and dpiit.claim_before_bid_deadline is True
            and dpiit.tender_permits_relaxation is True
            and status_is(dpiit.status, "VALID", "ACTIVE")
            and status_is(dpiit.identity_match, "EXACT")
            and exact_text_match(dpiit.entity_name, bidder.legal_name)
            and exact_text_match(dpiit.pan_reference, bidder.pan_reference)
            and dpiit.valid_through is not None
            and dpiit.valid_through >= context.bid_end_at.date()
            and has_certificate
        )
        evidence.update(
            {
                "dpiit_recognition_number": (
                    dpiit.recognition_number if dpiit else None
                ),
                "dpiit_valid_through": dpiit.valid_through if dpiit else None,
                "dpiit_certificate_present": has_certificate,
                "startup_relaxation_facts_satisfied": relaxation_valid,
            }
        )
        if relaxation_valid:
            return self.result(
                "COMPLIANT",
                "Below-threshold turnover is covered by the configured, factually verified Startup relaxation.",
                evidence=evidence,
                source_references=source_reference(dpiit),
            )
        return self.result(
            "NON_COMPLIANT",
            "Average turnover is below threshold and Startup relaxation conditions are not satisfied.",
            evidence=evidence,
            source_references=source_reference(dpiit),
        )


class FinancialDocumentEvaluator(RequirementEvaluator):
    requirement_code = "FIN-DOC-001"

    def evaluate(self, context, bidder, verification):
        missing = []
        if bidder.turnover is None:
            missing.append("turnover certificate")
        if bidder.audited_financials is None:
            missing.append("audited financial extracts")
        if bidder.financial_boq is None:
            missing.append("financial BOQ")
        evidence = {
            "turnover_certificate_present": bidder.turnover is not None,
            "audited_financials_present": bidder.audited_financials is not None,
            "financial_boq_present": bidder.financial_boq is not None,
        }
        if missing:
            return self.result(
                "MISSING",
                f"Required financial evidence is missing: {', '.join(missing)}.",
                evidence=evidence,
            )

        assert bidder.turnover and bidder.audited_financials and bidder.financial_boq
        usable = bool(
            bidder.turnover.fields.average_turnover is not None
            and bidder.audited_financials.fields.financial_years
            and bidder.financial_boq.fields.line_items
            and bidder.financial_boq.fields.total_bid_value is not None
        )
        entity_matches = all(
            exact_text_match(value, bidder.legal_name)
            for value in (
                bidder.turnover.fields.bidder_name,
                bidder.audited_financials.fields.bidder_name,
                bidder.financial_boq.fields.bidder_name,
            )
        )
        evidence.update(
            {
                "usable_financial_fields": usable,
                "financial_entity_matches": entity_matches,
                "audited_year_count": len(
                    bidder.audited_financials.fields.financial_years
                ),
            }
        )
        if not usable:
            return self.result(
                "NEEDS_REVIEW",
                "Financial documents are present but one or more are not usefully extracted.",
                evidence=evidence,
            )
        if not entity_matches:
            return self.result(
                "NON_COMPLIANT",
                "Financial packet does not consistently identify the bidding entity.",
                evidence=evidence,
            )
        return self.result(
            "COMPLIANT",
            "Turnover certificate, audited extracts, and financial BOQ are present and usable.",
            evidence=evidence,
        )


FINANCIAL_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    TurnoverEvaluator,
    FinancialDocumentEvaluator,
)
