from __future__ import annotations

import re

from app.schemas.normalized_documents import (
    AuditedFinancialsDocument,
    AuditedFinancialsFields,
    AuditedFinancialYear,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    canonicalize_label,
    parse_currency_amount,
    table_label_values,
    table_rows,
)


def _financial_year_key(value: str | None) -> str:
    return "".join(re.findall(r"\d", value or ""))[-6:]


class AuditedFinancialsNormalizer(BaseDocumentNormalizer):
    document_type = "AUDITED_FINANCIALS"

    field_aliases = {
        "bidder_name": ("Legal entity", "Bidder"),
        "pan_reference": ("PAN", "Identity reference"),
        "cin": ("Synthetic CIN", "CIN"),
        "auditor_name": ("Auditor",),
        "average_turnover": ("Average turnover",),
    }

    def _audit_metadata(self) -> dict[str, tuple[str, str | None]]:
        metadata: dict[str, tuple[str, str | None]] = {}
        reference_label = canonicalize_label("Audit extract reference")
        opinion_label = canonicalize_label("Audit opinion")
        for table in self.extraction.tables:
            values = table_label_values(table)
            reference = values.get(reference_label)
            if not reference:
                continue
            metadata[_financial_year_key(reference)] = (
                reference,
                values.get(opinion_label),
            )
        return metadata

    def _financial_years(self) -> list[AuditedFinancialYear]:
        metadata = self._audit_metadata()
        results: list[AuditedFinancialYear] = []
        for table in self.extraction.tables:
            for row in table_rows(table):
                financial_year = row.get(0)
                if not financial_year or not re.fullmatch(
                    r"FY\s+\d{4}-\d{2}", financial_year, re.IGNORECASE
                ):
                    continue
                reference, opinion = metadata.get(
                    _financial_year_key(financial_year),
                    (None, None),
                )
                results.append(
                    AuditedFinancialYear(
                        financial_year=financial_year,
                        revenue_from_operations=parse_currency_amount(
                            row.get(1)
                        ),
                        profit_before_tax=parse_currency_amount(row.get(2)),
                        closing_net_worth=parse_currency_amount(row.get(3)),
                        audited_status=row.get(4),
                        audit_reference=reference,
                        audit_opinion=opinion,
                    )
                )
        return results

    def normalize(self) -> AuditedFinancialsDocument:
        return AuditedFinancialsDocument(
            source_file=self.extraction.file_name,
            fields=AuditedFinancialsFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                cin=self.value("cin"),
                auditor_name=self.value("auditor_name"),
                average_turnover=parse_currency_amount(
                    self.value("average_turnover")
                ),
                financial_years=self._financial_years(),
            ),
        )
