from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from app.schemas.submission_ingestion import BidderImportMetadata
from app.services.document_processing.azure_document_intelligence import (
    AzureConfigurationError,
    AzureDocumentAuthenticationError,
    AzureDocumentIntelligenceService,
    AzureDocumentServiceError,
    DocumentExtractionError,
)
from app.services.document_processing.document_normalizer import (
    DocumentNormalizer,
    UnsupportedDocumentTypeError,
)
from app.services.document_processing.normalizers.base import (
    DocumentNormalizationError,
    normalize_whitespace,
)
from app.services.ingestion.archive import CollectedPackage
from app.services.ingestion.document_classifier import (
    DocumentClassification,
    classify_document,
    classify_document_content,
)
from app.services.ingestion.errors import (
    BidderIdentityConflictError,
    BidderIdentityExtractionError,
)


IDENTITY_TYPES = {
    "PAN_RECORD_REFERENCE",
    "GST_REGISTRATION",
    "UDYAM_REGISTRATION",
    "PRODUCT_DATASHEET",
}


@dataclass(slots=True)
class IdentityDiscoveryResult:
    bidder: BidderImportMetadata
    classifications: dict[str, DocumentClassification] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class BidderIdentityDiscoveryService:
    """Derive bidder identity from uploaded bidder evidence.

    Ingestion intentionally extracts only the minimum metadata required to create
    the bidder/submission safely. Full requirement extraction remains part of the
    assessment pipeline.
    """

    def __init__(self, settings) -> None:
        self.settings = settings

    def discover(self, package: CollectedPackage) -> IdentityDiscoveryResult:
        classifications = {
            document.filename.casefold(): classify_document(document.filename)
            for document in package.documents
        }
        normalized_by_type: dict[str, object] = {}
        warnings: list[str] = []

        # Known identity documents are processed first. Unknown filenames are
        # also inspected so officer uploads do not depend on synthetic names.
        ordered = sorted(
            package.documents,
            key=lambda document: self._priority(
                classifications[document.filename.casefold()].document_type
            ),
        )

        try:
            with AzureDocumentIntelligenceService(self.settings) as extractor:
                for document in ordered:
                    identity = document.filename.casefold()
                    classification = classifications[identity]
                    if (
                        classification.document_type not in IDENTITY_TYPES
                        and classification.document_type != "UNKNOWN"
                    ):
                        continue

                    try:
                        extraction = extractor.extract(document.local_path)
                    except (
                        AzureConfigurationError,
                        AzureDocumentAuthenticationError,
                        AzureDocumentServiceError,
                    ) as exc:
                        raise BidderIdentityExtractionError(
                            "Bidder identity extraction service is unavailable"
                        ) from exc
                    except DocumentExtractionError as exc:
                        warnings.append(
                            f"Could not extract identity evidence from {document.filename}: "
                            f"{type(exc).__name__}"
                        )
                        continue

                    if classification.document_type == "UNKNOWN":
                        classification = classify_document_content(extraction.content)
                        classifications[identity] = classification

                    if classification.document_type not in IDENTITY_TYPES:
                        continue

                    try:
                        normalized = DocumentNormalizer().normalize(
                            extraction,
                            document_type=classification.document_type,
                        )
                    except (UnsupportedDocumentTypeError, DocumentNormalizationError) as exc:
                        warnings.append(
                            f"Could not normalize identity evidence from {document.filename}: "
                            f"{type(exc).__name__}"
                        )
                        continue
                    normalized_by_type.setdefault(
                        classification.document_type,
                        normalized,
                    )
        except BidderIdentityExtractionError:
            raise

        bidder = self._build_bidder(
            normalized_by_type=normalized_by_type,
            classifications=classifications.values(),
            package=package,
        )
        return IdentityDiscoveryResult(
            bidder=bidder,
            classifications=classifications,
            warnings=warnings,
        )

    @staticmethod
    def _priority(document_type: str) -> int:
        priorities = {
            "PAN_RECORD_REFERENCE": 0,
            "GST_REGISTRATION": 1,
            "UDYAM_REGISTRATION": 2,
            "PRODUCT_DATASHEET": 3,
            "UNKNOWN": 4,
        }
        return priorities.get(document_type, 10)

    def _build_bidder(
        self,
        *,
        normalized_by_type: dict[str, object],
        classifications: Iterable[DocumentClassification],
        package: CollectedPackage,
    ) -> BidderImportMetadata:
        pan_doc = normalized_by_type.get("PAN_RECORD_REFERENCE")
        gst_doc = normalized_by_type.get("GST_REGISTRATION")
        udyam_doc = normalized_by_type.get("UDYAM_REGISTRATION")
        product_doc = normalized_by_type.get("PRODUCT_DATASHEET")

        pan_fields = getattr(pan_doc, "fields", None)
        gst_fields = getattr(gst_doc, "fields", None)
        udyam_fields = getattr(udyam_doc, "fields", None)
        product_fields = getattr(product_doc, "fields", None)

        pan_candidates = self._nonempty(
            getattr(pan_fields, "pan_reference", None),
            getattr(gst_fields, "pan_reference", None),
            getattr(udyam_fields, "pan_reference", None),
            self._pan_from_gstin(getattr(gst_fields, "gstin", None)),
        )
        canonical_pans = {self._canonical_reference(value) for value in pan_candidates}
        if len(canonical_pans) > 1:
            raise BidderIdentityConflictError(
                "PAN identity differs across uploaded PAN/GST/Udyam evidence"
            )
        if not canonical_pans:
            raise BidderIdentityExtractionError(
                "Could not determine bidder PAN from uploaded evidence"
            )
        pan_reference = next(iter(canonical_pans))

        name_candidates = self._nonempty(
            getattr(pan_fields, "legal_name", None),
            getattr(gst_fields, "legal_name", None),
            getattr(udyam_fields, "enterprise_name", None),
        )
        canonical_names = {
            self._canonical_legal_name(value): normalize_whitespace(value)
            for value in name_candidates
        }
        if len(canonical_names) > 1:
            raise BidderIdentityConflictError(
                "Bidder legal name differs across uploaded PAN/GST/Udyam evidence"
            )
        if not canonical_names:
            raise BidderIdentityExtractionError(
                "Could not determine bidder legal name from uploaded evidence"
            )
        bidder_name = next(iter(canonical_names.values()))

        types = {item.document_type for item in classifications}
        filenames = "\n".join(
            document.filename.casefold() for document in package.documents
        )

        gst_reference = self._clean_reference(getattr(gst_fields, "gstin", None))
        udyam_reference = self._clean_reference(
            getattr(udyam_fields, "udyam_number", None)
        )
        entity_type = self._first_nonempty(
            getattr(pan_fields, "entity_category", None),
            getattr(gst_fields, "constitution", None),
            getattr(udyam_fields, "organisation_type", None),
        )
        registered_address = self._first_nonempty(
            getattr(udyam_fields, "registered_address", None),
            getattr(gst_fields, "principal_place", None),
        )

        offered_make = self._first_nonempty(
            getattr(product_fields, "brand", None),
            getattr(product_fields, "oem_name", None),
        )
        offered_model = self._first_nonempty(
            getattr(product_fields, "model", None)
        )

        mse_claimed = bool(udyam_reference or "UDYAM_REGISTRATION" in types)
        startup_claimed = "DPIIT_RECOGNITION" in types
        nsic_claimed = "NSIC_REGISTRATION" in types
        emd_exemption_claimed = (
            "emd_exemption" in filenames
            or "exemption_proof" in filenames
            or nsic_claimed
        )

        return BidderImportMetadata(
            bidder_name=bidder_name,
            entity_type=entity_type,
            registered_address=registered_address,
            pan_reference=pan_reference,
            gst_reference=gst_reference,
            udyam_reference=udyam_reference,
            is_synthetic=False,
            mse_claimed=mse_claimed,
            startup_claimed=startup_claimed,
            nsic_claimed=nsic_claimed,
            emd_exemption_claimed=emd_exemption_claimed,
            offered_make=offered_make,
            offered_model=offered_model,
        )

    @staticmethod
    def _canonical_reference(value: str) -> str:
        return re.sub(r"\s+", "", normalize_whitespace(value)).upper()

    @classmethod
    def _clean_reference(cls, value: str | None) -> str | None:
        if not value:
            return None
        return cls._canonical_reference(value)

    @staticmethod
    def _canonical_legal_name(value: str) -> str:
        cleaned = normalize_whitespace(value).casefold()
        cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
        tokens = cleaned.split()
        aliases = {
            "pvt": "private",
            "ltd": "limited",
            "co": "company",
        }
        return " ".join(aliases.get(token, token) for token in tokens)

    @staticmethod
    def _pan_from_gstin(gstin: str | None) -> str | None:
        if not gstin:
            return None
        compact = re.sub(r"\s+", "", gstin).upper()
        if len(compact) == 15:
            return compact[2:12]
        return None

    @staticmethod
    def _nonempty(*values: str | None) -> list[str]:
        return [normalize_whitespace(value) for value in values if normalize_whitespace(value)]

    @staticmethod
    def _first_nonempty(*values: str | None) -> str | None:
        for value in values:
            cleaned = normalize_whitespace(value)
            if cleaned:
                return cleaned
        return None
