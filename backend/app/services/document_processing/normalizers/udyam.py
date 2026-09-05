from __future__ import annotations

from app.schemas.normalized_documents import (
    UdyamRegistrationDocument,
    UdyamRegistrationFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    clean_extracted_value,
    normalize_decision,
    parse_date_value,
)


class UdyamRegistrationNormalizer(BaseDocumentNormalizer):
    document_type = "UDYAM_REGISTRATION"

    field_aliases = {
        "udyam_number": ("Udyam reference", "Udyam number"),
        "enterprise_name": ("Enterprise name",),
        "organisation_type": ("Organisation type", "Organization type"),
        "enterprise_classification": ("Enterprise classification",),
        "registration_date": ("Registration date",),
        "pan_reference": ("PAN reference", "Identity reference"),
        "gstin": ("GST reference", "GSTIN"),
        "registered_address": ("Registered address",),
        "status": ("Status shown", "Registration status"),
    }

    def _activities(self) -> tuple[list[str], list[str]]:
        codes: list[str] = []
        activities: list[str] = []
        for table in self.extraction.tables:
            rows: dict[int, dict[int, str]] = {}
            for cell in table.cells:
                cleaned = clean_extracted_value(cell.content)
                if cleaned:
                    rows.setdefault(cell.row_index, {})[
                        cell.column_index
                    ] = cleaned

            for row_index in sorted(rows):
                row = rows[row_index]
                code = row.get(0)
                activity = row.get(1)
                relevance = row.get(2)
                if (
                    code
                    and code.upper().startswith("SYN-NIC-")
                    and activity
                    and relevance
                    and relevance.upper() == "RELEVANT"
                ):
                    codes.append(code)
                    activities.append(activity)
        return codes, activities

    def normalize(self) -> UdyamRegistrationDocument:
        activity_codes, registered_activities = self._activities()
        return UdyamRegistrationDocument(
            source_file=self.extraction.file_name,
            fields=UdyamRegistrationFields(
                udyam_number=self.value("udyam_number"),
                enterprise_name=self.value("enterprise_name"),
                organisation_type=self.value("organisation_type"),
                enterprise_classification=self.value(
                    "enterprise_classification"
                ),
                registration_date=parse_date_value(
                    self.value("registration_date")
                ),
                pan_reference=self.value("pan_reference"),
                gstin=self.value("gstin"),
                registered_address=self.value("registered_address"),
                status=normalize_decision(self.value("status")),
                activity_codes=activity_codes,
                registered_activities=registered_activities,
            ),
        )
