"""Document-specific normalization services."""

from app.services.document_processing.normalizers.audited_financials import (
    AuditedFinancialsNormalizer,
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


__all__ = [
    "AuditedFinancialsNormalizer",
    "EmdEvidenceNormalizer",
    "EpfoContributionStatusNormalizer",
    "EpfoRegistrationNormalizer",
    "EsicContributionStatusNormalizer",
    "EsicRegistrationNormalizer",
    "FinancialBoqNormalizer",
    "GstRegistrationNormalizer",
    "LocalContentNormalizer",
    "NoBlacklistingDeclarationNormalizer",
    "OemAuthorizationNormalizer",
    "PanRecordNormalizer",
    "ProductDatasheetNormalizer",
    "SimilarExperienceNormalizer",
    "TechnicalComplianceMatrixNormalizer",
    "TurnoverCertificateNormalizer",
    "UdyamRegistrationNormalizer",
    "WarrantySlaUndertakingNormalizer",
]
