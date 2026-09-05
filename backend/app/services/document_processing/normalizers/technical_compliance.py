from __future__ import annotations

import re

from app.schemas.normalized_documents import (
    TechnicalComplianceMatrixDocument,
    TechnicalComplianceMatrixFields,
    TechnicalComplianceRow,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    table_rows,
)


class TechnicalComplianceMatrixNormalizer(BaseDocumentNormalizer):
    document_type = "TECHNICAL_COMPLIANCE_MATRIX"

    field_aliases = {
        "bidder_name": ("Bidder",),
        "pan_reference": ("Identity reference", "PAN reference"),
        "oem_name": ("OEM",),
        "brand": ("Brand",),
        "model": ("Model",),
        "sku": ("SKU",),
    }

    def _technical_rows(self) -> list[TechnicalComplianceRow]:
        results: list[TechnicalComplianceRow] = []
        for table in self.extraction.tables:
            for row in table_rows(table):
                code = row.get(0)
                if not code or not re.fullmatch(
                    r"TECH-\d{3}[A-Z]", code, re.IGNORECASE
                ):
                    continue
                results.append(
                    TechnicalComplianceRow(
                        technical_code=code.upper(),
                        tender_requirement=row.get(1),
                        offered_specification=row.get(2),
                        compliance_claim=row.get(3),
                        evidence_reference=row.get(4),
                    )
                )
        return results

    def normalize(self) -> TechnicalComplianceMatrixDocument:
        return TechnicalComplianceMatrixDocument(
            source_file=self.extraction.file_name,
            fields=TechnicalComplianceMatrixFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                oem_name=self.value("oem_name"),
                brand=self.value("brand"),
                model=self.value("model"),
                sku=self.value("sku"),
                rows=self._technical_rows(),
            ),
        )
