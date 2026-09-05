from __future__ import annotations

from app.schemas.normalized_documents import (
    NoBlacklistingDeclarationDocument,
    NoBlacklistingDeclarationFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    parse_date_value,
)


class NoBlacklistingDeclarationNormalizer(BaseDocumentNormalizer):
    document_type = "NO_BLACKLISTING_DECLARATION"

    field_aliases = {
        "bidder_name": ("Legal name", "Bidder"),
        "pan_reference": ("PAN", "Identity reference"),
        "cin": ("Synthetic CIN", "CIN"),
        "registered_address": ("Registered address",),
        "declaration_status": ("Status declared",),
        "declaration_date": ("Declaration date",),
        "signatory_name": ("Representative", "Signatory name"),
        "signatory_role": ("Designation", "Signatory role"),
    }

    def normalize(self) -> NoBlacklistingDeclarationDocument:
        declaration_status = self.value("declaration_status")
        return NoBlacklistingDeclarationDocument(
            source_file=self.extraction.file_name,
            fields=NoBlacklistingDeclarationFields(
                bidder_name=self.value("bidder_name"),
                pan_reference=self.value("pan_reference"),
                cin=self.value("cin"),
                registered_address=self.value("registered_address"),
                declaration_status=declaration_status,
                declaration_date=parse_date_value(
                    self.value("declaration_date")
                ),
                signatory_name=self.value("signatory_name"),
                signatory_role=self.value("signatory_role"),
                declaration_summary=declaration_status,
            ),
        )
