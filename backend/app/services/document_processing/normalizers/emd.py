from __future__ import annotations

from app.schemas.normalized_documents import EmdEvidenceDocument, EmdEvidenceFields
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    normalize_decision,
    parse_currency_amount,
    parse_date_value,
    table_rows,
)


class EmdEvidenceNormalizer(BaseDocumentNormalizer):
    document_type = "EMD_EVIDENCE"

    field_aliases = {
        "bidder_name": ("Bidder", "Enterprise name"),
        "pan_reference": ("PAN reference", "Identity reference"),
        "bid_number": ("Synthetic bid", "Bid number"),
        "amount": ("EMD amount otherwise payable", "EMD amount"),
        "payment_reference": ("Payment reference",),
        "payment_date": ("Payment date",),
        "payment_status": ("Payment status",),
        "exemption_claimed": ("Exemption claimed",),
        "exemption_basis": ("Relevant category", "Exemption basis"),
        "claim_date": ("Claim date",),
        "udyam_reference": ("Udyam reference",),
        "nsic_reference": ("NSIC SPR reference", "NSIC reference"),
        "certificate_reference": ("Certificate reference",),
        "valid_from": ("Valid from",),
        "valid_through": ("Valid through",),
        "registration_status": ("Registration status",),
        "monetary_limit": ("Monetary limit",),
        "representative": ("Representative",),
    }

    def _evidence_type(self) -> str | None:
        if self.value("payment_reference"):
            return "PAYMENT"
        if self.value("certificate_reference"):
            return "EXEMPTION_SUPPORT"
        if self.value("exemption_claimed"):
            return "EXEMPTION_CLAIM"
        return None

    def _covered_categories(self) -> list[str]:
        categories: list[str] = []
        for table in self.extraction.tables:
            for row in table_rows(table):
                code = row.get(0)
                category = row.get(1)
                if (
                    code
                    and code.upper().startswith("SYN-NSIC-CAT-")
                    and category
                ):
                    categories.append(category)
        return categories

    def normalize(self) -> EmdEvidenceDocument:
        exemption_claimed = normalize_decision(
            self.value("exemption_claimed")
        )
        return EmdEvidenceDocument(
            source_file=self.extraction.file_name,
            fields=EmdEvidenceFields(
                evidence_type=self._evidence_type(),
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                bid_number=self.value("bid_number"),
                amount=parse_currency_amount(self.value("amount")),
                payment_reference=self.value("payment_reference"),
                payment_date=parse_date_value(self.value("payment_date")),
                payment_status=self.value("payment_status"),
                exemption_claimed=(
                    True
                    if exemption_claimed == "YES"
                    else False if exemption_claimed == "NO" else None
                ),
                exemption_basis=self.value("exemption_basis"),
                claim_date=parse_date_value(self.value("claim_date")),
                udyam_reference=self.value("udyam_reference"),
                nsic_reference=self.value("nsic_reference"),
                certificate_reference=self.value("certificate_reference"),
                valid_from=parse_date_value(self.value("valid_from")),
                valid_through=parse_date_value(self.value("valid_through")),
                registration_status=normalize_decision(
                    self.value("registration_status")
                ),
                monetary_limit=parse_currency_amount(
                    self.value("monetary_limit")
                ),
                covered_categories=self._covered_categories(),
                representative=self.value("representative"),
            ),
        )
