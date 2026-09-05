from __future__ import annotations

from app.schemas.normalized_documents import (
    GstRegistrationDocument,
    GstRegistrationFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    normalize_decision,
    parse_date_value,
)


class GstRegistrationNormalizer(BaseDocumentNormalizer):
    document_type = "GST_REGISTRATION"

    field_aliases = {
        "gstin": ("GSTIN", "GST identification number"),
        "legal_name": ("Legal name", "GST legal name"),
        "trade_name": ("Trade name",),
        "pan_reference": ("PAN reference", "Identity reference"),
        "constitution": ("Constitution",),
        "effective_registration_date": (
            "Effective registration date",
            "Registration effective date",
        ),
        "registration_type": ("Registration type",),
        "registration_status": (
            "Status shown on document",
            "Registration status",
        ),
        "principal_place": (
            "Principal place",
            "Principal place of business",
        ),
        "document_reference": ("Document reference",),
    }

    def normalize(self) -> GstRegistrationDocument:
        return GstRegistrationDocument(
            source_file=self.extraction.file_name,
            fields=GstRegistrationFields(
                gstin=self.value("gstin"),
                legal_name=self.value("legal_name"),
                trade_name=self.value("trade_name"),
                pan_reference=self.value("pan_reference"),
                constitution=self.value("constitution"),
                effective_registration_date=parse_date_value(
                    self.value("effective_registration_date")
                ),
                registration_type=self.value("registration_type"),
                registration_status=normalize_decision(
                    self.value("registration_status")
                ),
                principal_place=self.value("principal_place"),
                document_reference=self.value("document_reference"),
            ),
        )
