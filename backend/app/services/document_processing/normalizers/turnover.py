from __future__ import annotations

import re

from app.schemas.normalized_documents import (
    FinancialYearTurnover,
    TurnoverCertificateDocument,
    TurnoverCertificateFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    parse_currency_amount,
    parse_date_value,
    table_rows,
)


class TurnoverCertificateNormalizer(BaseDocumentNormalizer):
    document_type = "TURNOVER_CERTIFICATE"

    field_aliases = {
        "bidder_name": ("Bidder",),
        "pan_reference": ("Identity reference", "PAN reference"),
        "average_turnover": ("Certified average", "Three-year average"),
        "certificate_date": ("Certificate date",),
        "professional_name": ("Name", "Professional"),
        "professional_role": ("Designation",),
        "membership_reference": ("Membership reference",),
        "firm_name": ("Firm",),
        "firm_reference": ("Firm reference",),
    }

    def _financial_years(self) -> list[FinancialYearTurnover]:
        results: list[FinancialYearTurnover] = []
        for table in self.extraction.tables:
            for row in table_rows(table):
                financial_year = row.get(0)
                if not financial_year or not re.fullmatch(
                    r"FY\s+\d{4}-\d{2}", financial_year, re.IGNORECASE
                ):
                    continue
                results.append(
                    FinancialYearTurnover(
                        financial_year=financial_year,
                        turnover=parse_currency_amount(row.get(1)),
                        audit_reference=row.get(2),
                    )
                )
        return results

    def normalize(self) -> TurnoverCertificateDocument:
        return TurnoverCertificateDocument(
            source_file=self.extraction.file_name,
            fields=TurnoverCertificateFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                financial_years=self._financial_years(),
                average_turnover=parse_currency_amount(
                    self.value("average_turnover")
                ),
                certificate_date=parse_date_value(
                    self.value("certificate_date")
                ),
                professional_name=self.value("professional_name"),
                professional_role=self.value("professional_role"),
                membership_reference=self.value("membership_reference"),
                firm_name=self.value("firm_name"),
                firm_reference=self.value("firm_reference"),
            ),
        )
