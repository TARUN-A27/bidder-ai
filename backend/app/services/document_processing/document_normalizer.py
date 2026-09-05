from __future__ import annotations

import re

from app.schemas.document_extraction import DocumentExtractionResult
from app.schemas.normalized_documents import NormalizedDocument
from app.services.document_processing.normalizers.audited_financials import (
    AuditedFinancialsNormalizer,
)
from app.services.document_processing.normalizers.base import (
    DocumentNormalizationError,
)
from app.services.document_processing.normalizers.epfo_contribution import (
    EpfoContributionStatusNormalizer,
)
from app.services.document_processing.normalizers.epfo_registration import (
    EpfoRegistrationNormalizer,
)
from app.services.document_processing.normalizers.esic_contribution import (
    EsicContributionStatusNormalizer,
)
from app.services.document_processing.normalizers.esic_registration import (
    EsicRegistrationNormalizer,
)
from app.services.document_processing.normalizers.financial_boq import (
    FinancialBoqNormalizer,
)
from app.services.document_processing.normalizers.gst import (
    GstRegistrationNormalizer,
)
from app.services.document_processing.normalizers.local_content import (
    LocalContentNormalizer,
)
from app.services.document_processing.normalizers.no_blacklisting import (
    NoBlacklistingDeclarationNormalizer,
)
from app.services.document_processing.normalizers.oem_authorization import (
    OemAuthorizationNormalizer,
)
from app.services.document_processing.normalizers.pan import PanRecordNormalizer
from app.services.document_processing.normalizers.product_datasheet import (
    ProductDatasheetNormalizer,
)
from app.services.document_processing.normalizers.similar_experience import (
    SimilarExperienceNormalizer,
)
from app.services.document_processing.normalizers.technical_compliance import (
    TechnicalComplianceMatrixNormalizer,
)
from app.services.document_processing.normalizers.turnover import (
    TurnoverCertificateNormalizer,
)
from app.services.document_processing.normalizers.udyam import (
    UdyamRegistrationNormalizer,
)
from app.services.document_processing.normalizers.warranty_sla import (
    WarrantySlaUndertakingNormalizer,
)
from app.services.document_processing.normalizers.emd import (
    EmdEvidenceNormalizer,
)


class UnsupportedDocumentTypeError(DocumentNormalizationError):
    """Raised when no supported document normalizer can be selected."""


class DocumentNormalizer:
    _normalizer_classes = {
        "PAN_RECORD_REFERENCE": PanRecordNormalizer,
        "OEM_AUTHORIZATION": OemAuthorizationNormalizer,
        "PRODUCT_DATASHEET": ProductDatasheetNormalizer,
        "GST_REGISTRATION": GstRegistrationNormalizer,
        "UDYAM_REGISTRATION": UdyamRegistrationNormalizer,
        "EPFO_REGISTRATION": EpfoRegistrationNormalizer,
        "EPFO_CONTRIBUTION_STATUS": EpfoContributionStatusNormalizer,
        "ESIC_REGISTRATION": EsicRegistrationNormalizer,
        "ESIC_CONTRIBUTION_STATUS": EsicContributionStatusNormalizer,
        "TURNOVER_CERTIFICATE": TurnoverCertificateNormalizer,
        "AUDITED_FINANCIALS": AuditedFinancialsNormalizer,
        "SIMILAR_EXPERIENCE": SimilarExperienceNormalizer,
        "LOCAL_CONTENT": LocalContentNormalizer,
        "TECHNICAL_COMPLIANCE_MATRIX": (
            TechnicalComplianceMatrixNormalizer
        ),
        "WARRANTY_SLA_UNDERTAKING": WarrantySlaUndertakingNormalizer,
        "EMD_EVIDENCE": EmdEvidenceNormalizer,
        "FINANCIAL_BOQ": FinancialBoqNormalizer,
        "NO_BLACKLISTING_DECLARATION": (
            NoBlacklistingDeclarationNormalizer
        ),
    }

    _explicit_type_aliases = {
        "PAN": "PAN_RECORD_REFERENCE",
        "PAN_RECORD": "PAN_RECORD_REFERENCE",
        "PAN_RECORD_REFERENCE": "PAN_RECORD_REFERENCE",
        "OEM_AUTH": "OEM_AUTHORIZATION",
        "OEM_AUTHORIZATION": "OEM_AUTHORIZATION",
        "OEM_AUTHORIZATION_LETTER": "OEM_AUTHORIZATION",
        "PRODUCT_DATASHEET": "PRODUCT_DATASHEET",
        "OFFERED_MODEL_DATASHEET": "PRODUCT_DATASHEET",
        "OFFERED_MODEL_PRODUCT_DATASHEET": "PRODUCT_DATASHEET",
        "GST": "GST_REGISTRATION",
        "GST_REGISTRATION": "GST_REGISTRATION",
        "GST_REGISTRATION_CERTIFICATE": "GST_REGISTRATION",
        "UDYAM": "UDYAM_REGISTRATION",
        "UDYAM_REGISTRATION": "UDYAM_REGISTRATION",
        "UDYAM_REGISTRATION_CERTIFICATE": "UDYAM_REGISTRATION",
        "EPFO_REGISTRATION": "EPFO_REGISTRATION",
        "EPFO_REGISTRATION_LETTER": "EPFO_REGISTRATION",
        "EPFO_CONTRIBUTION": "EPFO_CONTRIBUTION_STATUS",
        "EPFO_CONTRIBUTION_STATUS": "EPFO_CONTRIBUTION_STATUS",
        "ESIC_REGISTRATION": "ESIC_REGISTRATION",
        "ESIC_C11_REGISTRATION": "ESIC_REGISTRATION",
        "ESIC_C11_REGISTRATION_LETTER": "ESIC_REGISTRATION",
        "ESIC_CONTRIBUTION": "ESIC_CONTRIBUTION_STATUS",
        "ESIC_CONTRIBUTION_STATUS": "ESIC_CONTRIBUTION_STATUS",
        "TURNOVER": "TURNOVER_CERTIFICATE",
        "TURNOVER_CERTIFICATE": "TURNOVER_CERTIFICATE",
        "CA_AVERAGE_TURNOVER_CERTIFICATE": "TURNOVER_CERTIFICATE",
        "AUDITED_FINANCIALS": "AUDITED_FINANCIALS",
        "AUDITED_FINANCIAL_EXTRACTS": "AUDITED_FINANCIALS",
        "SIMILAR_EXPERIENCE": "SIMILAR_EXPERIENCE",
        "SIMILAR_EXPERIENCE_EVIDENCE": "SIMILAR_EXPERIENCE",
        "LOCAL_CONTENT": "LOCAL_CONTENT",
        "LOCAL_CONTENT_CERTIFICATE": "LOCAL_CONTENT",
        "TECHNICAL_COMPLIANCE": "TECHNICAL_COMPLIANCE_MATRIX",
        "TECHNICAL_COMPLIANCE_MATRIX": "TECHNICAL_COMPLIANCE_MATRIX",
        "WARRANTY_SLA": "WARRANTY_SLA_UNDERTAKING",
        "WARRANTY_SLA_UNDERTAKING": "WARRANTY_SLA_UNDERTAKING",
        "EMD": "EMD_EVIDENCE",
        "EMD_EVIDENCE": "EMD_EVIDENCE",
        "EMD_EXEMPTION_PROOF": "EMD_EVIDENCE",
        "NSIC_SPR_CERTIFICATE": "EMD_EVIDENCE",
        "FINANCIAL_BOQ": "FINANCIAL_BOQ",
        "FINANCIAL_BID_BOQ": "FINANCIAL_BOQ",
        "NO_BLACKLISTING": "NO_BLACKLISTING_DECLARATION",
        "NO_BLACKLISTING_DECLARATION": "NO_BLACKLISTING_DECLARATION",
    }

    def normalize(
        self,
        extraction: DocumentExtractionResult,
        document_type: str | None = None,
    ) -> NormalizedDocument:
        resolved_type = self._resolve_document_type(
            extraction=extraction,
            explicit_type=document_type,
        )
        normalizer_class = self._normalizer_classes[resolved_type]
        return normalizer_class(extraction).normalize()

    def _resolve_document_type(
        self,
        extraction: DocumentExtractionResult,
        explicit_type: str | None,
    ) -> str:
        if explicit_type:
            normalized_type = self._canonical_type(explicit_type)
            resolved_type = self._explicit_type_aliases.get(normalized_type)
            if not resolved_type:
                raise UnsupportedDocumentTypeError(
                    f"Unsupported document type: {explicit_type}"
                )
            return resolved_type

        file_token = self._canonical_type(extraction.file_name)
        if re.search(
            r"(?:^|_)PAN_(?:RECORD_)?REFERENCE(?:_|$)",
            file_token,
        ):
            return "PAN_RECORD_REFERENCE"
        if re.search(
            r"(?:^|_)OEM_(?:AUTHORIZATION|AUTHORISATION)"
            r"(?:_LETTER)?(?:_|$)",
            file_token,
        ):
            return "OEM_AUTHORIZATION"
        if (
            "OFFERED_MODEL_PRODUCT_DATASHEET" in file_token
            or "PRODUCT_DATASHEET" in file_token
        ):
            return "PRODUCT_DATASHEET"
        if "GST_REGISTRATION_CERTIFICATE" in file_token:
            return "GST_REGISTRATION"
        if "UDYAM_REGISTRATION_CERTIFICATE" in file_token:
            return "UDYAM_REGISTRATION"
        if "EPFO_CONTRIBUTION_STATUS" in file_token:
            return "EPFO_CONTRIBUTION_STATUS"
        if "EPFO_REGISTRATION_LETTER" in file_token:
            return "EPFO_REGISTRATION"
        if "ESIC_CONTRIBUTION_STATUS" in file_token:
            return "ESIC_CONTRIBUTION_STATUS"
        if re.search(
            r"(?:^|_)ESIC_(?:C11_)?REGISTRATION_LETTER(?:_|$)",
            file_token,
        ):
            return "ESIC_REGISTRATION"
        if "CA_AVERAGE_TURNOVER_CERTIFICATE" in file_token:
            return "TURNOVER_CERTIFICATE"
        if "AUDITED_FINANCIAL_EXTRACTS" in file_token:
            return "AUDITED_FINANCIALS"
        if "SIMILAR_EXPERIENCE_EVIDENCE_BUNDLE" in file_token:
            return "SIMILAR_EXPERIENCE"
        if "LOCAL_CONTENT_DECLARATION_AND_CA_CERTIFICATE" in file_token:
            return "LOCAL_CONTENT"
        if "TECHNICAL_COMPLIANCE_SHEET" in file_token:
            return "TECHNICAL_COMPLIANCE_MATRIX"
        if "WARRANTY_SLA_AND_NO_CLOUD_UPLOAD_UNDERTAKING" in file_token:
            return "WARRANTY_SLA_UNDERTAKING"
        if "EMD_EXEMPTION_PROOF" in file_token:
            return "EMD_EVIDENCE"
        if "NSIC_SPR_CERTIFICATE" in file_token:
            return "EMD_EVIDENCE"
        if "FINANCIAL_BID_BOQ" in file_token:
            return "FINANCIAL_BOQ"
        if "NO_BLACKLISTING_SELF_DECLARATION" in file_token:
            return "NO_BLACKLISTING_DECLARATION"
        raise UnsupportedDocumentTypeError(
            f"Unsupported document type for file: {extraction.file_name}"
        )

    @staticmethod
    def _canonical_type(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9]+", "_", value.upper()).strip("_")
