from __future__ import annotations

from app.schemas.normalized_documents import (
    EsicContributionStatusDocument,
    EsicContributionStatusFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    extract_integer,
    find_table_row,
    normalize_decision,
    parse_currency_amount,
    parse_date_value,
)


class EsicContributionStatusNormalizer(BaseDocumentNormalizer):
    document_type = "ESIC_CONTRIBUTION_STATUS"

    field_aliases = {
        "pan_reference": ("Identity reference", "PAN reference"),
        "latest_compliance_period": (
            "Latest due period",
            "Latest period due at bid closing",
        ),
        "statutory_due_date": ("Synthetic due date", "Statutory due date"),
        "payment_date": ("Payment date",),
        "outstanding_amount": ("Outstanding amount",),
        "registration_status": ("Registration status",),
        "challan_reference": (
            "Synthetic challan reference",
            "Challan reference",
        ),
    }

    def normalize(self) -> EsicContributionStatusDocument:
        latest_period = self.value("latest_compliance_period")
        latest_row = find_table_row(self.extraction, latest_period)
        return EsicContributionStatusDocument(
            source_file=self.extraction.file_name,
            fields=EsicContributionStatusFields(
                pan_reference=self.value("pan_reference"),
                latest_compliance_period=latest_period,
                statutory_due_date=parse_date_value(
                    self.value("statutory_due_date")
                ),
                payment_date=parse_date_value(self.value("payment_date")),
                covered_employee_count=extract_integer(latest_row.get(1)),
                wage_base_amount=parse_currency_amount(latest_row.get(2)),
                contribution_amount=parse_currency_amount(latest_row.get(3)),
                outstanding_amount=parse_currency_amount(
                    self.value("outstanding_amount")
                ),
                registration_status=normalize_decision(
                    self.value("registration_status")
                ),
                challan_reference=self.value("challan_reference"),
            ),
        )
