from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.schemas.normalized_documents import (
    LocalContentComponent,
    LocalContentDocument,
    LocalContentFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    parse_currency_amount,
    parse_date_value,
    parse_percentage_value,
    table_rows,
)


def _decimal_value(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


class LocalContentNormalizer(BaseDocumentNormalizer):
    document_type = "LOCAL_CONTENT"

    field_aliases = {
        "bidder_name": ("Bidder",),
        "pan_reference": ("Identity reference", "PAN reference"),
        "oem_name": ("OEM",),
        "offered_model": ("Offered product", "Offered model"),
        "bid_number": ("Synthetic bid number", "Bid number"),
        "local_content_percentage": (
            "Verified percentage",
            "Declared local content",
        ),
        "domestic_value": ("Verified local units", "Local value addition"),
        "total_value": ("Verified total units",),
        "calculation_basis": ("Calculation basis",),
        "stated_classification": ("Classification",),
        "primary_location": ("Primary value-addition location",),
        "professional_name": ("Professional",),
        "professional_role": ("Designation",),
        "membership_reference": ("Membership reference",),
        "firm_name": ("Firm",),
        "firm_reference": ("Firm reference",),
        "certificate_date": ("Certificate date",),
    }

    def _components(self) -> list[LocalContentComponent]:
        results: list[LocalContentComponent] = []
        for table in self.extraction.tables:
            if table.column_count != 4:
                continue
            for row in table_rows(table):
                component = row.get(0)
                if not component or component.upper() == "TOTAL":
                    continue
                results.append(
                    LocalContentComponent(
                        component=component,
                        total_value_units=_decimal_value(row.get(1)),
                        local_value_units=_decimal_value(row.get(2)),
                        value_addition_location=row.get(3),
                    )
                )
        return results

    def normalize(self) -> LocalContentDocument:
        return LocalContentDocument(
            source_file=self.extraction.file_name,
            fields=LocalContentFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                oem_name=self.value("oem_name"),
                offered_model=self.value("offered_model"),
                bid_number=self.value("bid_number"),
                local_content_percentage=parse_percentage_value(
                    self.value("local_content_percentage")
                ),
                domestic_value=parse_currency_amount(
                    self.value("domestic_value")
                ),
                total_value=parse_currency_amount(self.value("total_value")),
                calculation_basis=self.value("calculation_basis"),
                stated_classification=self.value("stated_classification"),
                primary_value_addition_location=self.value(
                    "primary_location"
                ),
                professional_name=self.value("professional_name"),
                professional_role=self.value("professional_role"),
                membership_reference=self.value("membership_reference"),
                firm_name=self.value("firm_name"),
                firm_reference=self.value("firm_reference"),
                certificate_date=parse_date_value(
                    self.value("certificate_date")
                ),
                components=self._components(),
            ),
        )
