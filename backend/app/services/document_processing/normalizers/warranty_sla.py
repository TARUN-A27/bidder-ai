from __future__ import annotations

import re

from app.schemas.normalized_documents import (
    WarrantySlaUndertakingDocument,
    WarrantySlaUndertakingFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    canonicalize_label,
    parse_date_value,
    parse_percentage_value,
)


class WarrantySlaUndertakingNormalizer(BaseDocumentNormalizer):
    document_type = "WARRANTY_SLA_UNDERTAKING"

    field_aliases = {
        "bidder_name": ("Bidder",),
        "pan_reference": ("Identity reference", "PAN reference"),
        "offered_model": ("Product", "Offered model"),
        "warranty": ("Warranty",),
        "parts_and_labour": ("Parts and labour",),
        "minimum_uptime": ("Minimum uptime",),
        "service_response": ("Service response",),
        "resolution_or_standby": ("Resolution or standby",),
        "firmware_updates": ("Firmware and driver updates",),
        "oem_support_reference": ("OEM support basis",),
        "representative": ("Representative",),
        "undertaking_date": ("Date", "Undertaking date"),
    }

    @staticmethod
    def _warranty_years(value: str | None) -> int | None:
        if not value:
            return None
        digit_match = re.search(r"\b(\d+)\s*[- ]?years?\b", value, re.I)
        if digit_match:
            return int(digit_match.group(1))
        word_values = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
        }
        canonical_value = canonicalize_label(value)
        for word, number in word_values.items():
            if re.search(rf"\b{word}\s+year\b", canonical_value):
                return number
        return None

    def normalize(self) -> WarrantySlaUndertakingDocument:
        warranty = self.value("warranty")
        canonical_warranty = canonicalize_label(warranty)
        canonical_content = canonicalize_label(self.extraction.content)
        return WarrantySlaUndertakingDocument(
            source_file=self.extraction.file_name,
            fields=WarrantySlaUndertakingFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                offered_model=self.value("offered_model"),
                warranty_years=self._warranty_years(warranty),
                onsite_warranty=(
                    True if "onsite warranty" in canonical_warranty else None
                ),
                warranty_text=warranty,
                parts_and_labour=self.value("parts_and_labour"),
                minimum_uptime_percentage=parse_percentage_value(
                    self.value("minimum_uptime")
                ),
                service_response=self.value("service_response"),
                resolution_or_standby=self.value("resolution_or_standby"),
                firmware_and_driver_updates=self.value("firmware_updates"),
                no_cloud_upload=(
                    True
                    if "without mandatory external cloud upload"
                    in canonical_content
                    else None
                ),
                local_processing_commitment=(
                    True
                    if "normal scanning will operate locally"
                    in canonical_content
                    else None
                ),
                oem_support_reference=self.value("oem_support_reference"),
                representative=self.value("representative"),
                undertaking_date=parse_date_value(
                    self.value("undertaking_date")
                ),
            ),
        )
