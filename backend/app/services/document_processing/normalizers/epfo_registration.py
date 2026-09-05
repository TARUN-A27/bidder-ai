from __future__ import annotations

from app.schemas.normalized_documents import (
    EpfoRegistrationDocument,
    EpfoRegistrationFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    normalize_decision,
    parse_date_value,
)


class EpfoRegistrationNormalizer(BaseDocumentNormalizer):
    document_type = "EPFO_REGISTRATION"

    field_aliases = {
        "establishment_id": ("Establishment code", "EPFO code"),
        "establishment_name": ("Establishment name",),
        "pan_reference": ("PAN reference", "Identity reference"),
        "address": ("Registered address", "Establishment address"),
        "registration_date": (
            "Coverage effective date",
            "Registration date",
        ),
        "coverage_status": ("Establishment status", "Coverage status"),
        "compliance_office": ("Compliance office",),
        "document_reference": (
            "Registration reference",
            "Document reference",
        ),
        "record_date": ("Record date",),
    }

    def normalize(self) -> EpfoRegistrationDocument:
        return EpfoRegistrationDocument(
            source_file=self.extraction.file_name,
            fields=EpfoRegistrationFields(
                establishment_id=self.value("establishment_id"),
                establishment_name=self.value("establishment_name"),
                pan_reference=self.value("pan_reference"),
                address=self.value("address"),
                registration_date=parse_date_value(
                    self.value("registration_date")
                ),
                coverage_status=normalize_decision(
                    self.value("coverage_status")
                ),
                compliance_office=self.value("compliance_office"),
                document_reference=self.value("document_reference"),
                record_date=parse_date_value(self.value("record_date")),
            ),
        )
