from __future__ import annotations

from app.services.compliance.base import (
    RequirementEvaluator,
    source_reference,
    status_is,
)


class SimilarExperienceEvaluator(RequirementEvaluator):
    requirement_code = "EXP-SIM-001"

    def evaluate(self, context, bidder, verification):
        if bidder.experience is None:
            return self.result("MISSING", "Submitted similar-experience evidence is absent.")
        source = verification.issuer_verification
        if source is None:
            return self.result(
                "NEEDS_REVIEW",
                "Experience evidence has no authoritative issuer verification.",
            )

        experience_years = source.experience_years
        cutoff = context.bid_end_at.date().replace(
            year=context.bid_end_at.year - 5
        )
        qualifying_records = []
        ambiguous_records = []
        for record in source.records:
            similar_scope = bool(
                record.scope
                and any(
                    token in record.scope.casefold()
                    for token in ("scanner", "scanning", "imaging")
                )
            )
            completed = status_is(record.completion_status, "COMPLETED")
            within_window = bool(
                record.completion_date
                and cutoff <= record.completion_date <= context.bid_end_at.date()
            )
            if record.value is None or record.completion_date is None or not record.scope:
                ambiguous_records.append(record.work_order_number)
            if similar_scope and completed and within_window and record.value is not None:
                qualifying_records.append(record)

        qualifying_values = [record.value for record in qualifying_records]
        two_order_route = (
            sum(value >= context.two_order_threshold_inr for value in qualifying_values)
            >= 2
        )
        single_order_route = any(
            value >= context.single_order_threshold_inr
            for value in qualifying_values
        )
        evidence = {
            "experience_years": experience_years,
            "minimum_experience_years": context.minimum_experience_years,
            "qualifying_orders": [
                {
                    "work_order_number": record.work_order_number,
                    "value": record.value,
                    "completion_date": record.completion_date,
                }
                for record in qualifying_records
            ],
            "two_order_route_satisfied": two_order_route,
            "single_order_route_satisfied": single_order_route,
        }
        if experience_years is None:
            return self.result(
                "NEEDS_REVIEW",
                "Issuer evidence does not state the bidder's experience duration.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if (
            experience_years >= context.minimum_experience_years
            and (two_order_route or single_order_route)
        ):
            return self.result(
                "COMPLIANT",
                "Verified experience duration and completed similar orders satisfy the configured routes.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        if ambiguous_records and not qualifying_records:
            evidence["ambiguous_records"] = ambiguous_records
            return self.result(
                "NEEDS_REVIEW",
                "Experience records are present but lack facts needed for a definitive evaluation.",
                evidence=evidence,
                source_references=source_reference(source),
            )
        return self.result(
            "NON_COMPLIANT",
            "Verified experience duration or qualifying-order values do not meet the tender rule.",
            evidence=evidence,
            source_references=source_reference(source),
        )


EXPERIENCE_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    SimilarExperienceEvaluator,
)
