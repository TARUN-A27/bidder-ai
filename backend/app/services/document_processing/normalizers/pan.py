from __future__ import annotations

from app.schemas.normalized_documents import PanRecordDocument, PanRecordFields
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    normalize_decision,
    parse_date_value,
)


class PanRecordNormalizer(BaseDocumentNormalizer):
    document_type = "PAN_RECORD_REFERENCE"

    field_aliases = {
        "pan_reference": (
            "PAN reference",
            "PAN record reference",
            "Permanent Account Number",
            "PAN number",
        ),
        "legal_name": (
            "Legal name",
            "PAN legal name",
            "Name of entity",
        ),
        "entity_category": (
            "Entity category",
            "Category of entity",
            "Entity type",
        ),
        "incorporation_date": (
            "Incorporation date",
            "Date of incorporation",
        ),
        "identity_status": (
            "Identity status",
            "PAN status",
            "Record status",
        ),
        "name_match_basis": (
            "Name-match basis",
            "Name match basis",
            "Matching basis",
        ),
        "bid_cover_match": (
            "PAN record vs bid cover",
            "Bid cover match",
        ),
        "gst_name_match": (
            "PAN record vs GST legal name",
            "GST legal name match",
            "GST name match",
        ),
        "udyam_name_match": (
            "PAN record vs Udyam enterprise name",
            "Udyam enterprise name match",
            "Udyam name match",
        ),
        "financial_evidence_match": (
            "PAN record vs financial evidence",
            "Financial evidence match",
            "Financial name match",
        ),
    }

    def normalize(self) -> PanRecordDocument:
        return PanRecordDocument(
            source_file=self.extraction.file_name,
            fields=PanRecordFields(
                pan_reference=self.value("pan_reference"),
                legal_name=self.value("legal_name"),
                entity_category=normalize_decision(
                    self.value("entity_category")
                ),
                incorporation_date=parse_date_value(
                    self.value("incorporation_date")
                ),
                identity_status=normalize_decision(
                    self.value("identity_status")
                ),
                name_match_basis=self.value("name_match_basis"),
                bid_cover_match=normalize_decision(
                    self.value("bid_cover_match")
                ),
                gst_name_match=normalize_decision(
                    self.value("gst_name_match")
                ),
                udyam_name_match=normalize_decision(
                    self.value("udyam_name_match")
                ),
                financial_evidence_match=normalize_decision(
                    self.value("financial_evidence_match")
                ),
            ),
        )
