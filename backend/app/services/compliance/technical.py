from __future__ import annotations

import re

from app.schemas.compliance import TechnicalSubResult
from app.services.compliance.base import (
    RequirementEvaluator,
    exact_text_match,
    source_reference,
    status_is,
)


def _numbers(value: str) -> list[int]:
    return [int(token.replace(",", "")) for token in re.findall(r"\d[\d,]*", value)]


def _contains_all(value: str, tokens: tuple[str, ...]) -> bool:
    folded = value.casefold()
    return all(token in folded for token in tokens)


def _minimum_number(required: str) -> int | None:
    values = _numbers(required)
    return values[0] if values else None


class TechnicalSpecificationEvaluator(RequirementEvaluator):
    requirement_code = "TECH-SPEC-001"

    def evaluate(self, context, bidder, verification):
        matrix = bidder.technical_matrix
        submitted_datasheet = bidder.product_datasheet
        authoritative = verification.product_datasheet
        if matrix is None or submitted_datasheet is None:
            return self.result(
                "MISSING",
                "Required technical matrix or submitted product datasheet is absent.",
            )
        if authoritative is None:
            return self.result(
                "NEEDS_REVIEW",
                "Authoritative OEM datasheet record is unavailable.",
            )

        matrix_rows = {row.technical_code: row for row in matrix.fields.rows}
        technical_results: list[TechnicalSubResult] = []
        for requirement in context.technical_requirements:
            code = requirement.technical_code
            observed = authoritative.technical_specifications.get(code)
            if code not in matrix_rows:
                technical_results.append(
                    TechnicalSubResult(
                        technical_code=code,
                        status="MISSING",
                        required=requirement.minimum_requirement,
                        observed=observed,
                        reason="Submitted technical matrix row is absent.",
                    )
                )
                continue
            if not observed:
                technical_results.append(
                    TechnicalSubResult(
                        technical_code=code,
                        status="NEEDS_REVIEW",
                        required=requirement.minimum_requirement,
                        observed=None,
                        reason="Authoritative OEM specification is unavailable.",
                    )
                )
                continue
            passed, reason = self._evaluate_subcheck(
                code,
                requirement.minimum_requirement,
                observed,
                bidder,
                verification,
                context,
            )
            technical_results.append(
                TechnicalSubResult(
                    technical_code=code,
                    status="COMPLIANT" if passed else "NON_COMPLIANT",
                    required=requirement.minimum_requirement,
                    observed=observed,
                    reason=reason,
                    source_references=source_reference(authoritative),
                )
            )

        quality_findings = [
            finding
            for finding in bidder.manifest.quality_findings
            if "technical_compliance" in finding.file_name.casefold()
            and any(
                token in finding.condition.casefold()
                for token in ("low_contrast", "unclear", "unreadable")
            )
        ]
        statuses = {item.status for item in technical_results}
        evidence = {
            "offered_model": authoritative.model,
            "technical_results": [
                item.model_dump(mode="json") for item in technical_results
            ],
            "quality_findings": [
                item.model_dump(mode="json") for item in quality_findings
            ],
        }
        references = source_reference(authoritative)
        references.extend(source_reference(verification.product_certification))
        if "NON_COMPLIANT" in statuses:
            failed = [
                item.technical_code
                for item in technical_results
                if item.status == "NON_COMPLIANT"
            ]
            return self.result(
                "NON_COMPLIANT",
                f"Authoritative product facts fail essential checks: {', '.join(failed)}.",
                evidence=evidence,
                source_references=references,
            )
        if "MISSING" in statuses and quality_findings:
            return self.result(
                "NEEDS_REVIEW",
                "Technical facts pass where readable, but documented page quality prevents definitive review of all matrix rows.",
                evidence=evidence,
                source_references=references,
            )
        if "MISSING" in statuses:
            return self.result(
                "MISSING",
                "One or more required technical matrix rows are absent.",
                evidence=evidence,
                source_references=references,
            )
        if "NEEDS_REVIEW" in statuses or quality_findings:
            return self.result(
                "NEEDS_REVIEW",
                "Technical facts pass, but submitted technical evidence has a documented readability ambiguity.",
                evidence=evidence,
                source_references=references,
            )
        return self.result(
            "COMPLIANT",
            "All configured essential technical sub-requirements are independently supported.",
            evidence=evidence,
            source_references=references,
        )

    def _evaluate_subcheck(
        self,
        code,
        required,
        observed,
        bidder,
        verification,
        context,
    ):
        folded = observed.casefold()
        if code == "TECH-001A":
            passed = _contains_all(observed, ("a4", "sheet-fed", "duplex", "scanner"))
        elif code == "TECH-001B":
            required_values = _numbers(required)
            observed_values = _numbers(observed)
            passed = bool(
                len(required_values) >= 2
                and len(observed_values) >= 2
                and observed_values[0] >= required_values[0]
                and observed_values[1] >= required_values[1]
            )
        elif code == "TECH-001C":
            minimum = _minimum_number(required)
            actual = _minimum_number(observed)
            passed = bool(minimum is not None and actual is not None and actual >= minimum)
        elif code == "TECH-001D":
            minimum = _minimum_number(required)
            actual = _minimum_number(observed)
            passed = bool(minimum is not None and actual is not None and actual >= minimum)
        elif code == "TECH-001E":
            minimum = _minimum_number(required)
            actual = _minimum_number(observed)
            passed = bool(minimum is not None and actual is not None and actual >= minimum)
        elif code == "TECH-001F":
            passed = _contains_all(observed, ("colour", "grayscale", "monochrome"))
        elif code == "TECH-001G":
            passed = "double-feed" in folded and (
                "ultrasonic" in folded or "equivalent" in folded
            )
        elif code == "TECH-001H":
            negative_ethernet = bool(
                re.search(r"(?:gigabit\s+ethernet\s+not supported|no\s+gigabit|without\s+ethernet)", folded)
            )
            passed = bool(
                re.search(r"usb\s*3(?:\.|\b)", folded)
                and "gigabit ethernet" in folded
                and not negative_ethernet
            )
        elif code == "TECH-001I":
            passed = "twain" in folded and "documented" in folded and any(
                token in folded for token in ("interface", "sdk", "api")
            )
        elif code == "TECH-001J":
            passed = _contains_all(observed, ("deskew", "blank-page", "orientation"))
        elif code == "TECH-001K":
            required_values = _numbers(required)
            observed_values = _numbers(observed)
            passed = bool(
                len(required_values) >= 2
                and len(observed_values) >= 2
                and observed_values[0] >= required_values[0]
                and observed_values[1] >= required_values[1]
            )
        elif code == "TECH-001L":
            warranty = bidder.warranty.fields if bidder.warranty else None
            passed = bool(
                warranty
                and warranty.warranty_years is not None
                and warranty.warranty_years >= context.warranty_years
                and warranty.onsite_warranty is True
                and "warranty" in folded
            )
        elif code == "TECH-001M":
            certificate = verification.product_certification
            passed = bool(
                certificate
                and status_is(
                    certificate.status,
                    context.product_certificate_required_status,
                )
                and exact_text_match(
                    certificate.certificate_standard,
                    context.product_certificate_standard,
                )
                and certificate.exact_model_match is True
                and certificate.certificate_report_match is True
                and certificate.report_number
                and any(
                    exact_text_match(model, bidder.offered_model)
                    for model in certificate.covered_models
                )
                and certificate.valid_through is not None
                and certificate.valid_through >= context.bid_end_at.date()
            )
        elif code == "TECH-001N":
            warranty = bidder.warranty.fields if bidder.warranty else None
            passed = bool(
                warranty
                and warranty.no_cloud_upload is True
                and warranty.local_processing_commitment is True
                and "no mandatory external-cloud upload" in folded
            )
        else:
            return False, "No deterministic evaluator exists for this configured technical code."
        return passed, (
            "Authoritative and submitted factual evidence meet the configured requirement."
            if passed
            else "Observed factual specification does not meet the configured requirement."
        )


TECHNICAL_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    TechnicalSpecificationEvaluator,
)
