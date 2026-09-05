from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.normalized_documents import (
    AuditedFinancialsDocument,
    EmdEvidenceDocument,
    EpfoContributionStatusDocument,
    EpfoRegistrationDocument,
    EsicContributionStatusDocument,
    EsicRegistrationDocument,
    FinancialBoqDocument,
    GstRegistrationDocument,
    LocalContentDocument,
    NoBlacklistingDeclarationDocument,
    OemAuthorizationDocument,
    PanRecordDocument,
    ProductDatasheetDocument,
    SimilarExperienceDocument,
    TechnicalComplianceMatrixDocument,
    TurnoverCertificateDocument,
    UdyamRegistrationDocument,
    WarrantySlaUndertakingDocument,
)


ComplianceStatus = Literal[
    "COMPLIANT",
    "NON_COMPLIANT",
    "MISSING",
    "NEEDS_REVIEW",
    "NOT_APPLICABLE",
]


class RequirementEvaluationResult(BaseModel):
    requirement_code: str
    status: ComplianceStatus
    reason: str
    requires_human_review: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_references: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TechnicalRequirement(BaseModel):
    technical_code: str
    parameter: str
    minimum_requirement: str
    classification: str


class TechnicalSubResult(BaseModel):
    technical_code: str
    status: ComplianceStatus
    required: str
    observed: str | None = None
    reason: str
    source_references: list[str] = Field(default_factory=list)


class TenderRequirementContext(BaseModel):
    dataset_id: str
    bid_number: str
    bid_end_at: datetime
    offer_valid_through: date
    oem_authorization_required_through: date
    required_contribution_period: str
    turnover_threshold_inr: Decimal
    startup_relaxation_permitted: bool
    startup_relaxed_requirement_ids: list[str] = Field(default_factory=list)
    minimum_experience_years: float
    two_order_threshold_inr: Decimal
    single_order_threshold_inr: Decimal
    minimum_local_content_percent: float
    emd_amount_inr: Decimal
    warranty_years: int
    product_certificate_standard: str
    product_certificate_required_status: str
    technical_requirements: list[TechnicalRequirement]
    requirement_codes: list[str]
    allowed_statuses: list[ComplianceStatus]

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "TenderRequirementContext":
        tender = _required_mapping(config, "tender")
        security = _required_mapping(config, "security")
        preferences = _required_mapping(config, "purchase_preferences")
        startup = _required_mapping(config, "startup_turnover_relaxation")
        certificate = _required_mapping(config, "product_certificate_rule")
        requirements = config.get("requirements")
        technical = config.get("technical_specifications")
        if not isinstance(requirements, list) or not isinstance(technical, list):
            raise ValueError("Tender requirements and technical specifications are required")

        descriptions = {
            item["requirement_id"]: item.get("description", "")
            for item in requirements
            if isinstance(item, dict) and item.get("requirement_id")
        }
        turnover_match = re.search(
            r"at least INR\s+([\d.]+)\s+crore",
            descriptions.get("FIN-TURN-001", ""),
            re.IGNORECASE,
        )
        experience_match = re.search(
            r"Minimum\s+(\w+)\s+years.*?two completed orders of at least "
            r"INR\s+([\d.]+)\s+crore each.*?one completed order of at least "
            r"INR\s+([\d.]+)\s+crore",
            descriptions.get("EXP-SIM-001", ""),
            re.IGNORECASE,
        )
        period_match = re.search(
            r"through\s+([A-Za-z]+\s+\d{4})",
            descriptions.get("STAT-EPFO-002", ""),
            re.IGNORECASE,
        )
        if not turnover_match or not experience_match or not period_match:
            raise ValueError("Tender descriptions do not expose required thresholds")

        word_numbers = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
        }
        years_token = experience_match.group(1).casefold()
        try:
            experience_years = float(
                word_numbers[years_token]
                if years_token in word_numbers
                else int(years_token)
            )
        except ValueError as exc:
            raise ValueError("Unsupported experience-years value") from exc

        required_period = datetime.strptime(
            period_match.group(1).title(), "%B %Y"
        ).strftime("%Y-%m")
        crore = Decimal("10000000")
        allowed_statuses = config.get("allowed_requirement_statuses")
        if not isinstance(allowed_statuses, list):
            raise ValueError("Tender allowed requirement statuses are required")

        return cls(
            dataset_id=str(config["dataset_id"]),
            bid_number=str(tender["bid_number"]),
            bid_end_at=tender["bid_end_at"],
            offer_valid_through=tender["offer_valid_through"],
            oem_authorization_required_through=(
                tender["oem_authorization_required_through"]
            ),
            required_contribution_period=required_period,
            turnover_threshold_inr=Decimal(turnover_match.group(1)) * crore,
            startup_relaxation_permitted=bool(
                startup["permitted_by_this_tender"]
            ),
            startup_relaxed_requirement_ids=list(
                startup.get("relaxed_requirement_ids", [])
            ),
            minimum_experience_years=experience_years,
            two_order_threshold_inr=(
                Decimal(experience_match.group(2)) * crore
            ),
            single_order_threshold_inr=(
                Decimal(experience_match.group(3)) * crore
            ),
            minimum_local_content_percent=float(
                preferences["minimum_local_content_percent"]
            ),
            emd_amount_inr=Decimal(str(security["emd_amount_inr"])),
            warranty_years=int(tender["warranty_years"]),
            product_certificate_standard=str(certificate["standard"]),
            product_certificate_required_status=str(
                certificate["required_status_at_bid_close"]
            ).upper(),
            technical_requirements=[
                TechnicalRequirement(
                    technical_code=str(item["technical_id"]),
                    parameter=str(item["parameter"]),
                    minimum_requirement=str(item["minimum_requirement"]),
                    classification=str(item["classification"]),
                )
                for item in technical
            ],
            requirement_codes=[str(item["requirement_id"]) for item in requirements],
            allowed_statuses=allowed_statuses,
        )


class BidderClaims(BaseModel):
    mse_purchase_preference: bool = False
    emd_exemption: bool = False
    startup_turnover_relaxation: bool = False
    mii_purchase_preference: bool = False
    nsic_related_benefit: bool = False


class ManifestDocument(BaseModel):
    document_number: str
    file_name: str
    packet: str | None = None
    contains_bid_price_information: bool | None = None
    page_count: int | None = None
    sha256: str | None = None
    required_notice_present_on_every_page: bool | None = None
    canonical_bidder_pan: str | None = None
    offered_model_reference: str | None = None


class DocumentQualityFinding(BaseModel):
    file_name: str
    page: int | None = None
    condition: str


class MissingDocumentFinding(BaseModel):
    file_name: str
    requirement_id: str | None = None


class BidderSubmissionManifest(BaseModel):
    bidder_id: str
    bidder_name: str
    document_count: int
    technical_packet_contains_bid_price_information: bool | None = None
    financial_price_file: str | None = None
    documents: list[ManifestDocument] = Field(default_factory=list)
    quality_findings: list[DocumentQualityFinding] = Field(default_factory=list)
    material_contradictions: list[str] = Field(default_factory=list)
    deliberately_missing_documents: list[MissingDocumentFinding] = Field(
        default_factory=list
    )


class BidderEvidenceBundle(BaseModel):
    bidder_id: str
    legal_name: str
    pan_reference: str
    offered_model: str
    claims: BidderClaims
    manifest: BidderSubmissionManifest
    gst: GstRegistrationDocument | None = None
    pan: PanRecordDocument | None = None
    udyam: UdyamRegistrationDocument | None = None
    epfo_registration: EpfoRegistrationDocument | None = None
    epfo_contribution: EpfoContributionStatusDocument | None = None
    esic_registration: EsicRegistrationDocument | None = None
    esic_contribution: EsicContributionStatusDocument | None = None
    turnover: TurnoverCertificateDocument | None = None
    audited_financials: AuditedFinancialsDocument | None = None
    experience: SimilarExperienceDocument | None = None
    oem_authorization: OemAuthorizationDocument | None = None
    product_datasheet: ProductDatasheetDocument | None = None
    local_content: LocalContentDocument | None = None
    technical_matrix: TechnicalComplianceMatrixDocument | None = None
    warranty: WarrantySlaUndertakingDocument | None = None
    emd_documents: list[EmdEvidenceDocument] = Field(default_factory=list)
    financial_boq: FinancialBoqDocument | None = None
    no_blacklisting: NoBlacklistingDeclarationDocument | None = None


def _required_mapping(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Tender configuration section {key!r} is required")
    return value
