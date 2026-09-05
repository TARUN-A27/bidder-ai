from __future__ import annotations

from app.services.compliance.base import (
    RequirementEvaluator,
    exact_text_match,
)


class DocumentIntegrityEvaluator(RequirementEvaluator):
    requirement_code = "DOC-INTEGRITY-001"

    def evaluate(self, context, bidder, verification):
        manifest = bidder.manifest
        missing_files = [
            item.file_name for item in manifest.deliberately_missing_documents
        ]
        contradictions = self._find_material_contradictions(bidder, verification)
        unreadable = [
            finding
            for finding in manifest.quality_findings
            if any(
                token in finding.condition.casefold()
                for token in ("low_contrast", "unclear", "unreadable", "corrupt")
            )
        ]
        count_matches = manifest.document_count == len(manifest.documents)
        technical_price_leak = (
            manifest.technical_packet_contains_bid_price_information is True
        )
        evidence = {
            "declared_document_count": manifest.document_count,
            "manifest_document_count": len(manifest.documents),
            "missing_files": missing_files,
            "quality_findings": [item.model_dump(mode="json") for item in unreadable],
            "derived_material_contradictions": contradictions,
            "technical_packet_contains_bid_price_information": technical_price_leak,
        }
        if missing_files or technical_price_leak or len(contradictions) >= 2:
            return self.result(
                "NON_COMPLIANT",
                "Submission has a material missing document, packet violation, or multiple proven contradictions.",
                evidence=evidence,
            )
        if not count_matches or unreadable or contradictions:
            return self.result(
                "NEEDS_REVIEW",
                "Submission is present but has a readability, count, or consistency issue requiring review.",
                evidence=evidence,
            )
        return self.result(
            "COMPLIANT",
            "Manifested submission is complete, readable, and free of derived material contradictions.",
            evidence=evidence,
        )

    @staticmethod
    def _find_material_contradictions(bidder, verification):
        contradictions: list[str] = []
        if bidder.gst and verification.gst:
            submitted = bidder.gst.fields.registration_status
            authoritative = verification.gst.status_at_bid_close or verification.gst.status
            if submitted and authoritative and submitted.upper() != authoritative.upper():
                contradictions.append("GST registration state")
        if bidder.pan and verification.pan:
            if not exact_text_match(
                bidder.pan.fields.pan_reference, verification.pan.pan_reference
            ) or not exact_text_match(
                bidder.pan.fields.legal_name, verification.pan.legal_name
            ):
                contradictions.append("PAN identity")
        if bidder.local_content and verification.local_content:
            declared = bidder.local_content.fields.local_content_percentage
            verified = verification.local_content.verified_local_content_percentage
            if declared is not None and verified is not None and declared != verified:
                contradictions.append("local-content percentage")
        if bidder.no_blacklisting and verification.debarment:
            declaration = bidder.no_blacklisting.fields.declaration_status or ""
            if verification.debarment.active is True and "no active" in declaration.casefold():
                contradictions.append("debarment declaration")
        if bidder.technical_matrix and verification.product_datasheet:
            rows = {
                row.technical_code: row.offered_specification
                for row in bidder.technical_matrix.fields.rows
            }
            for code, authoritative in (
                verification.product_datasheet.technical_specifications.items()
            ):
                submitted = rows.get(code)
                if submitted and not exact_text_match(submitted, authoritative):
                    contradictions.append("technical specification claims")
                    break
        return contradictions


DOCUMENT_INTEGRITY_EVALUATORS: tuple[type[RequirementEvaluator], ...] = (
    DocumentIntegrityEvaluator,
)
