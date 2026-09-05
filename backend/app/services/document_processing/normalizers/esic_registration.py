from __future__ import annotations

from app.schemas.normalized_documents import (
    EsicRegistrationDocument,
    EsicRegistrationFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    normalize_decision,
    parse_date_value,
)


class EsicRegistrationNormalizer(BaseDocumentNormalizer):
    document_type = "ESIC_REGISTRATION"

    field_aliases = {
        "employer_code": ("Employer code", "ESIC employer code"),
        "employer_name": ("Employer name",),
        "pan_reference": ("PAN reference", "Identity reference"),
        "address": ("Registered address", "Employer address"),
        "registration_date": (
            "Coverage effective date",
            "Registration date",
        ),
        "coverage_status": ("Employer status", "Coverage status"),
        "branch_office": ("Synthetic branch office", "Branch office"),
        "document_reference": (
            "Registration reference",
            "Document reference",
        ),
    }

    def normalize(self) -> EsicRegistrationDocument:
        return EsicRegistrationDocument(
            source_file=self.extraction.file_name,
            fields=EsicRegistrationFields(
                employer_code=self.value("employer_code"),
                employer_name=self.value("employer_name"),
                pan_reference=self.value("pan_reference"),
                address=self.value("address"),
                registration_date=parse_date_value(
                    self.value("registration_date")
                ),
                coverage_status=normalize_decision(
                    self.value("coverage_status")
                ),
                branch_office=self.value("branch_office"),
                document_reference=self.value("document_reference"),
            ),
        )
