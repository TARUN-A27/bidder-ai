from __future__ import annotations

from app.schemas.normalized_documents import (
    EpfoContributionStatusDocument,
    EpfoContributionStatusFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    extract_integer,
    find_table_row,
    parse_currency_amount,
    parse_date_value,
)


class EpfoContributionStatusNormalizer(BaseDocumentNormalizer):
    document_type = "EPFO_CONTRIBUTION_STATUS"

    field_aliases = {
        "pan_reference": ("Identity reference", "PAN reference"),
        "latest_compliance_period": (
            "Latest period due at bid closing",
            "Latest due period",
        ),
        "statutory_due_date": (
            "Statutory due date used by synthetic tender",
            "Statutory due date",
        ),
        "payment_date": ("Payment date",),
        "outstanding_amount": ("Outstanding amount",),
        "ecr_reference": ("Synthetic ECR reference", "ECR reference"),
        "payment_reference": ("Payment reference",),
    }

    def normalize(self) -> EpfoContributionStatusDocument:
        latest_period = self.value("latest_compliance_period")
        latest_row = find_table_row(self.extraction, latest_period)
        return EpfoContributionStatusDocument(
            source_file=self.extraction.file_name,
            fields=EpfoContributionStatusFields(
                pan_reference=self.value("pan_reference"),
                latest_compliance_period=latest_period,
                statutory_due_date=parse_date_value(
                    self.value("statutory_due_date")
                ),
                payment_date=parse_date_value(self.value("payment_date")),
                employee_count=extract_integer(latest_row.get(1)),
                wage_base_amount=parse_currency_amount(latest_row.get(2)),
                employee_share_amount=parse_currency_amount(
                    latest_row.get(3)
                ),
                employer_share_amount=parse_currency_amount(
                    latest_row.get(4)
                ),
                outstanding_amount=parse_currency_amount(
                    self.value("outstanding_amount")
                ),
                ecr_reference=self.value("ecr_reference"),
                payment_reference=self.value("payment_reference"),
            ),
        )
