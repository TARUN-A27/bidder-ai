from __future__ import annotations

import re

from app.schemas.normalized_documents import (
    ExperienceRecord,
    SimilarExperienceDocument,
    SimilarExperienceFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    canonicalize_label,
    parse_currency_amount,
    parse_date_value,
    table_label_values,
)


class SimilarExperienceNormalizer(BaseDocumentNormalizer):
    document_type = "SIMILAR_EXPERIENCE"

    field_aliases = {
        "bidder_name": ("Bidder",),
        "pan_reference": ("Identity reference", "PAN reference"),
        "incorporation_date": ("Incorporation date",),
        "experience_years": ("Experience at bid closing",),
    }

    def _records(self) -> list[ExperienceRecord]:
        results: list[ExperienceRecord] = []
        required_label = canonicalize_label("Work order number")
        for table in self.extraction.tables:
            values = table_label_values(table)
            if required_label not in values:
                continue

            scope = values.get(canonicalize_label("Scope"))
            quantity_match = re.search(
                r"\bof\s+(\d[\d,]*)\s+", scope or "", re.IGNORECASE
            )
            results.append(
                ExperienceRecord(
                    work_order_number=values.get(required_label),
                    customer=values.get(canonicalize_label("Customer")),
                    customer_address=values.get(
                        canonicalize_label("Customer address")
                    ),
                    supplier=values.get(canonicalize_label("Supplier")),
                    project_description=scope,
                    quantity=(
                        int(quantity_match.group(1).replace(",", ""))
                        if quantity_match
                        else None
                    ),
                    order_value=parse_currency_amount(
                        values.get(canonicalize_label("Order value"))
                    ),
                    start_date=parse_date_value(
                        values.get(canonicalize_label("Start date"))
                    ),
                    scheduled_completion_date=parse_date_value(
                        values.get(
                            canonicalize_label("Scheduled completion")
                        )
                    ),
                    completion_date=parse_date_value(
                        values.get(canonicalize_label("Actual completion"))
                    ),
                    record_status=values.get(canonicalize_label("Status")),
                    performance_status=values.get(
                        canonicalize_label("Performance")
                    ),
                    certificate_reference=values.get(
                        canonicalize_label("Issuer reference")
                    ),
                )
            )
        return results

    def normalize(self) -> SimilarExperienceDocument:
        experience_value = self.value("experience_years")
        experience_match = re.search(
            r"\d+(?:\.\d+)?", experience_value or ""
        )
        return SimilarExperienceDocument(
            source_file=self.extraction.file_name,
            fields=SimilarExperienceFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                incorporation_date=parse_date_value(
                    self.value("incorporation_date")
                ),
                experience_years=(
                    float(experience_match.group(0))
                    if experience_match
                    else None
                ),
                records=self._records(),
            ),
        )
