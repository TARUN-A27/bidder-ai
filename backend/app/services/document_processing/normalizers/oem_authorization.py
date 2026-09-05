from __future__ import annotations

from app.schemas.normalized_documents import (
    OemAuthorizationDocument,
    OemAuthorizationFields,
)
from app.services.document_processing.normalizers.base import (
    BaseDocumentNormalizer,
    normalize_decision,
    parse_date_value,
)


class OemAuthorizationNormalizer(BaseDocumentNormalizer):
    document_type = "OEM_AUTHORIZATION"

    field_aliases = {
        "oem_legal_name": (
            "OEM legal name",
            "OEM name",
            "Manufacturer legal name",
        ),
        "oem_registry_reference": (
            "OEM registry reference",
            "OEM reference",
            "Registry reference",
        ),
        "authorization_number": (
            "Authorization number",
            "Authorisation number",
            "Authorization reference",
            "Authorisation reference",
        ),
        "issue_date": (
            "Issue date",
            "Date of issue",
            "Authorization issue date",
        ),
        "valid_through": (
            "Valid through",
            "Valid until",
            "Validity date",
            "Authorization validity",
        ),
        "authorized_bidder": (
            "Authorized bidder",
            "Authorised bidder",
            "Bidder legal name",
        ),
        "bidder_pan": (
            "Bidder PAN",
            "Authorized bidder PAN",
            "Authorised bidder PAN",
        ),
        "bid_number": (
            "Synthetic bid number",
            "Bid number",
            "GeM bid number",
        ),
        "offered_brand_model": (
            "Offered brand/model",
            "Offered brand and model",
            "Authorized model",
            "Authorised model",
        ),
        "sku": (
            "SKU",
            "Product SKU",
            "Model SKU",
        ),
        "bid_specific_authorization": (
            "Bid-specific authorization",
            "Bid specific authorization",
            "Bid-specific authorisation",
        ),
        "exact_model_covered": (
            "Exact model covered",
            "Model coverage",
        ),
        "supply_installation_authorized": (
            "Supply and installation",
            "Supply installation authorization",
            "Supply and installation authorization",
            "Supply and installation authorisation",
        ),
    }

    def normalize(self) -> OemAuthorizationDocument:
        return OemAuthorizationDocument(
            source_file=self.extraction.file_name,
            fields=OemAuthorizationFields(
                oem_legal_name=self.value("oem_legal_name"),
                oem_registry_reference=self.value("oem_registry_reference"),
                authorization_number=self.value("authorization_number"),
                issue_date=parse_date_value(self.value("issue_date")),
                valid_through=parse_date_value(self.value("valid_through")),
                authorized_bidder=self.value("authorized_bidder"),
                bidder_pan=self.value("bidder_pan"),
                bid_number=self.value("bid_number"),
                offered_brand_model=self.value("offered_brand_model"),
                sku=self.value("sku"),
                bid_specific_authorization=normalize_decision(
                    self.value("bid_specific_authorization")
                ),
                exact_model_covered=normalize_decision(
                    self.value("exact_model_covered")
                ),
                supply_installation_authorized=normalize_decision(
                    self.value("supply_installation_authorized")
                ),
            ),
        )
