from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.schemas.normalized_documents import (
    BoqLineItem,
    FinancialBoqDocument,
    FinancialBoqFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    canonicalize_label,
    parse_currency_amount,
    parse_percentage_value,
    table_rows,
)


class FinancialBoqNormalizer(BaseDocumentNormalizer):
    document_type = "FINANCIAL_BOQ"

    field_aliases = {
        "bidder_name": ("Bidder",),
        "pan_reference": ("Identity reference", "PAN reference"),
        "bid_number": ("Synthetic bid", "Bid number"),
        "total_taxable_value": ("Total taxable bid value",),
        "taxes": ("Synthetic GST at 18 percent", "Taxes"),
        "total_bid_value": ("Total landed bid value", "Total bid value"),
        "currency": ("Currency",),
        "price_validity": ("Price validity",),
        "representative": ("Authorized representative", "Representative"),
    }

    @staticmethod
    def _quantity(value: str | None) -> tuple[Decimal | None, str | None]:
        if not value:
            return None, None
        match = re.match(r"^(\d+(?:\.\d+)?)\s*(.*)$", value)
        if not match:
            return None, None
        try:
            quantity = Decimal(match.group(1))
        except InvalidOperation:
            return None, None
        unit = match.group(2).strip() or None
        return quantity, unit

    def _line_items(self) -> list[BoqLineItem]:
        items: list[BoqLineItem] = []
        for table in self.extraction.tables:
            if table.column_count != 5:
                continue
            for row in table_rows(table):
                line_number = row.get(0)
                if not line_number or not line_number.isdigit():
                    continue
                quantity_text = row.get(2)
                quantity, quantity_unit = self._quantity(quantity_text)
                items.append(
                    BoqLineItem(
                        line_number=int(line_number),
                        description=row.get(1),
                        quantity=quantity,
                        quantity_unit=quantity_unit,
                        quantity_text=quantity_text,
                        unit_rate=parse_currency_amount(row.get(3)),
                        line_total=parse_currency_amount(row.get(4)),
                    )
                )
        return items

    def _tax_percentage(self) -> float | None:
        for table in self.extraction.tables:
            for row in table_rows(table):
                label = row.get(0)
                if canonicalize_label(label).startswith("synthetic gst at "):
                    return parse_percentage_value(label)
        return None

    def normalize(self) -> FinancialBoqDocument:
        return FinancialBoqDocument(
            source_file=self.extraction.file_name,
            fields=FinancialBoqFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                bid_number=self.value("bid_number"),
                currency=self.value("currency"),
                line_items=self._line_items(),
                total_taxable_value=parse_currency_amount(
                    self.value("total_taxable_value")
                ),
                taxes=parse_currency_amount(self.value("taxes")),
                tax_percentage=self._tax_percentage(),
                total_bid_value=parse_currency_amount(
                    self.value("total_bid_value")
                ),
                price_validity=self.value("price_validity"),
                representative=self.value("representative"),
            ),
        )
