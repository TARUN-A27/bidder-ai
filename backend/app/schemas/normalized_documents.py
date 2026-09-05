from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PanRecordFields(BaseModel):
    pan_reference: str | None = None
    legal_name: str | None = None
    entity_category: str | None = None
    incorporation_date: date | None = None
    identity_status: str | None = None
    name_match_basis: str | None = None
    bid_cover_match: str | None = None
    gst_name_match: str | None = None
    udyam_name_match: str | None = None
    financial_evidence_match: str | None = None


class PanRecordDocument(BaseModel):
    document_type: Literal["PAN_RECORD_REFERENCE"] = "PAN_RECORD_REFERENCE"
    source_file: str
    fields: PanRecordFields


class OemAuthorizationFields(BaseModel):
    oem_legal_name: str | None = None
    oem_registry_reference: str | None = None
    authorization_number: str | None = None
    issue_date: date | None = None
    valid_through: date | None = None
    authorized_bidder: str | None = None
    bidder_pan: str | None = None
    bid_number: str | None = None
    offered_brand_model: str | None = None
    sku: str | None = None
    bid_specific_authorization: str | None = None
    exact_model_covered: str | None = None
    supply_installation_authorized: str | None = None


class OemAuthorizationDocument(BaseModel):
    document_type: Literal["OEM_AUTHORIZATION"] = "OEM_AUTHORIZATION"
    source_file: str
    fields: OemAuthorizationFields


class ProductDatasheetFields(BaseModel):
    oem_name: str | None = None
    brand: str | None = None
    model: str | None = None
    sku: str | None = None
    product_type: str | None = None
    scanning_speed_ppm: int | None = None
    duplex_speed_ipm: int | None = None
    optical_resolution_dpi: int | None = None
    adf_capacity_sheets: int | None = None
    recommended_daily_volume_pages: int | None = None
    supported_modes: list[str] = Field(default_factory=list)
    maximum_document_width_mm: int | None = None
    maximum_document_height_mm: int | None = None
    paper_detection: str | None = None
    usb: str | None = None
    network: str | None = None
    driver: str | None = None
    integration: str | None = None
    image_processing_features: list[str] = Field(default_factory=list)


class ProductDatasheetDocument(BaseModel):
    document_type: Literal["PRODUCT_DATASHEET"] = "PRODUCT_DATASHEET"
    source_file: str
    fields: ProductDatasheetFields


class GstRegistrationFields(BaseModel):
    gstin: str | None = None
    legal_name: str | None = None
    trade_name: str | None = None
    pan_reference: str | None = None
    constitution: str | None = None
    effective_registration_date: date | None = None
    registration_type: str | None = None
    registration_status: str | None = None
    principal_place: str | None = None
    document_reference: str | None = None


class GstRegistrationDocument(BaseModel):
    document_type: Literal["GST_REGISTRATION"] = "GST_REGISTRATION"
    source_file: str
    fields: GstRegistrationFields


class UdyamRegistrationFields(BaseModel):
    udyam_number: str | None = None
    enterprise_name: str | None = None
    organisation_type: str | None = None
    enterprise_classification: str | None = None
    registration_date: date | None = None
    pan_reference: str | None = None
    gstin: str | None = None
    registered_address: str | None = None
    status: str | None = None
    activity_codes: list[str] = Field(default_factory=list)
    registered_activities: list[str] = Field(default_factory=list)


class UdyamRegistrationDocument(BaseModel):
    document_type: Literal["UDYAM_REGISTRATION"] = "UDYAM_REGISTRATION"
    source_file: str
    fields: UdyamRegistrationFields


class EpfoRegistrationFields(BaseModel):
    establishment_id: str | None = None
    establishment_name: str | None = None
    pan_reference: str | None = None
    address: str | None = None
    registration_date: date | None = None
    coverage_status: str | None = None
    compliance_office: str | None = None
    document_reference: str | None = None
    record_date: date | None = None


class EpfoRegistrationDocument(BaseModel):
    document_type: Literal["EPFO_REGISTRATION"] = "EPFO_REGISTRATION"
    source_file: str
    fields: EpfoRegistrationFields


class EpfoContributionStatusFields(BaseModel):
    pan_reference: str | None = None
    latest_compliance_period: str | None = None
    statutory_due_date: date | None = None
    payment_date: date | None = None
    employee_count: int | None = None
    wage_base_amount: Decimal | None = None
    employee_share_amount: Decimal | None = None
    employer_share_amount: Decimal | None = None
    outstanding_amount: Decimal | None = None
    ecr_reference: str | None = None
    payment_reference: str | None = None


class EpfoContributionStatusDocument(BaseModel):
    document_type: Literal["EPFO_CONTRIBUTION_STATUS"] = (
        "EPFO_CONTRIBUTION_STATUS"
    )
    source_file: str
    fields: EpfoContributionStatusFields


class EsicRegistrationFields(BaseModel):
    employer_code: str | None = None
    employer_name: str | None = None
    pan_reference: str | None = None
    address: str | None = None
    registration_date: date | None = None
    coverage_status: str | None = None
    branch_office: str | None = None
    document_reference: str | None = None


class EsicRegistrationDocument(BaseModel):
    document_type: Literal["ESIC_REGISTRATION"] = "ESIC_REGISTRATION"
    source_file: str
    fields: EsicRegistrationFields


class EsicContributionStatusFields(BaseModel):
    pan_reference: str | None = None
    latest_compliance_period: str | None = None
    statutory_due_date: date | None = None
    payment_date: date | None = None
    covered_employee_count: int | None = None
    wage_base_amount: Decimal | None = None
    contribution_amount: Decimal | None = None
    outstanding_amount: Decimal | None = None
    registration_status: str | None = None
    challan_reference: str | None = None


class EsicContributionStatusDocument(BaseModel):
    document_type: Literal["ESIC_CONTRIBUTION_STATUS"] = (
        "ESIC_CONTRIBUTION_STATUS"
    )
    source_file: str
    fields: EsicContributionStatusFields


class FinancialYearTurnover(BaseModel):
    financial_year: str
    turnover: Decimal | None = None
    audit_reference: str | None = None


class TurnoverCertificateFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    financial_years: list[FinancialYearTurnover] = Field(default_factory=list)
    average_turnover: Decimal | None = None
    certificate_number: str | None = None
    certificate_date: date | None = None
    professional_name: str | None = None
    professional_role: str | None = None
    membership_reference: str | None = None
    firm_name: str | None = None
    firm_reference: str | None = None
    document_reference: str | None = None


class TurnoverCertificateDocument(BaseModel):
    document_type: Literal["TURNOVER_CERTIFICATE"] = "TURNOVER_CERTIFICATE"
    source_file: str
    fields: TurnoverCertificateFields


class AuditedFinancialYear(BaseModel):
    financial_year: str
    revenue_from_operations: Decimal | None = None
    profit_before_tax: Decimal | None = None
    closing_net_worth: Decimal | None = None
    audited_status: str | None = None
    audit_reference: str | None = None
    audit_opinion: str | None = None


class AuditedFinancialsFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    cin: str | None = None
    auditor_name: str | None = None
    average_turnover: Decimal | None = None
    financial_years: list[AuditedFinancialYear] = Field(default_factory=list)
    document_reference: str | None = None


class AuditedFinancialsDocument(BaseModel):
    document_type: Literal["AUDITED_FINANCIALS"] = "AUDITED_FINANCIALS"
    source_file: str
    fields: AuditedFinancialsFields


class ExperienceRecord(BaseModel):
    work_order_number: str | None = None
    customer: str | None = None
    customer_address: str | None = None
    supplier: str | None = None
    project_description: str | None = None
    quantity: int | None = None
    order_value: Decimal | None = None
    start_date: date | None = None
    scheduled_completion_date: date | None = None
    completion_date: date | None = None
    record_status: str | None = None
    performance_status: str | None = None
    certificate_reference: str | None = None


class SimilarExperienceFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    incorporation_date: date | None = None
    experience_years: float | None = None
    records: list[ExperienceRecord] = Field(default_factory=list)
    document_reference: str | None = None


class SimilarExperienceDocument(BaseModel):
    document_type: Literal["SIMILAR_EXPERIENCE"] = "SIMILAR_EXPERIENCE"
    source_file: str
    fields: SimilarExperienceFields


class LocalContentComponent(BaseModel):
    component: str
    total_value_units: Decimal | None = None
    local_value_units: Decimal | None = None
    value_addition_location: str | None = None


class LocalContentFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    oem_name: str | None = None
    offered_model: str | None = None
    bid_number: str | None = None
    local_content_percentage: float | None = None
    domestic_value: Decimal | None = None
    total_value: Decimal | None = None
    calculation_basis: str | None = None
    stated_classification: str | None = None
    primary_value_addition_location: str | None = None
    professional_name: str | None = None
    professional_role: str | None = None
    membership_reference: str | None = None
    firm_name: str | None = None
    firm_reference: str | None = None
    certificate_number: str | None = None
    certificate_date: date | None = None
    components: list[LocalContentComponent] = Field(default_factory=list)
    document_reference: str | None = None


class LocalContentDocument(BaseModel):
    document_type: Literal["LOCAL_CONTENT"] = "LOCAL_CONTENT"
    source_file: str
    fields: LocalContentFields


class TechnicalComplianceRow(BaseModel):
    technical_code: str
    parameter: str | None = None
    tender_requirement: str | None = None
    offered_specification: str | None = None
    compliance_claim: str | None = None
    evidence_reference: str | None = None
    remarks: str | None = None


class TechnicalComplianceMatrixFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    oem_name: str | None = None
    brand: str | None = None
    model: str | None = None
    sku: str | None = None
    rows: list[TechnicalComplianceRow] = Field(default_factory=list)
    document_reference: str | None = None


class TechnicalComplianceMatrixDocument(BaseModel):
    document_type: Literal["TECHNICAL_COMPLIANCE_MATRIX"] = (
        "TECHNICAL_COMPLIANCE_MATRIX"
    )
    source_file: str
    fields: TechnicalComplianceMatrixFields


class WarrantySlaUndertakingFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    offered_model: str | None = None
    warranty_years: int | None = None
    onsite_warranty: bool | None = None
    warranty_text: str | None = None
    parts_and_labour: str | None = None
    minimum_uptime_percentage: float | None = None
    service_response: str | None = None
    resolution_or_standby: str | None = None
    firmware_and_driver_updates: str | None = None
    no_cloud_upload: bool | None = None
    local_processing_commitment: bool | None = None
    oem_support_reference: str | None = None
    representative: str | None = None
    undertaking_date: date | None = None
    document_reference: str | None = None


class WarrantySlaUndertakingDocument(BaseModel):
    document_type: Literal["WARRANTY_SLA_UNDERTAKING"] = (
        "WARRANTY_SLA_UNDERTAKING"
    )
    source_file: str
    fields: WarrantySlaUndertakingFields


class EmdEvidenceFields(BaseModel):
    evidence_type: Literal[
        "PAYMENT",
        "EXEMPTION_CLAIM",
        "EXEMPTION_SUPPORT",
    ] | None = None
    bidder_name: str | None = None
    pan_reference: str | None = None
    bid_number: str | None = None
    amount: Decimal | None = None
    payment_reference: str | None = None
    payment_date: date | None = None
    payment_status: str | None = None
    exemption_claimed: bool | None = None
    exemption_basis: str | None = None
    claim_date: date | None = None
    udyam_reference: str | None = None
    nsic_reference: str | None = None
    certificate_reference: str | None = None
    valid_from: date | None = None
    valid_through: date | None = None
    registration_status: str | None = None
    monetary_limit: Decimal | None = None
    covered_categories: list[str] = Field(default_factory=list)
    representative: str | None = None
    document_reference: str | None = None


class EmdEvidenceDocument(BaseModel):
    document_type: Literal["EMD_EVIDENCE"] = "EMD_EVIDENCE"
    source_file: str
    fields: EmdEvidenceFields


class BoqLineItem(BaseModel):
    line_number: int | None = None
    description: str | None = None
    quantity: Decimal | None = None
    quantity_unit: str | None = None
    quantity_text: str | None = None
    unit_rate: Decimal | None = None
    line_total: Decimal | None = None


class FinancialBoqFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    bid_number: str | None = None
    currency: str | None = None
    line_items: list[BoqLineItem] = Field(default_factory=list)
    total_taxable_value: Decimal | None = None
    taxes: Decimal | None = None
    tax_percentage: float | None = None
    total_bid_value: Decimal | None = None
    price_validity: str | None = None
    representative: str | None = None
    document_reference: str | None = None


class FinancialBoqDocument(BaseModel):
    document_type: Literal["FINANCIAL_BOQ"] = "FINANCIAL_BOQ"
    source_file: str
    fields: FinancialBoqFields


class NoBlacklistingDeclarationFields(BaseModel):
    bidder_name: str | None = None
    pan_reference: str | None = None
    cin: str | None = None
    registered_address: str | None = None
    declaration_status: str | None = None
    declaration_date: date | None = None
    signatory_name: str | None = None
    signatory_role: str | None = None
    declaration_summary: str | None = None
    document_reference: str | None = None


class NoBlacklistingDeclarationDocument(BaseModel):
    document_type: Literal["NO_BLACKLISTING_DECLARATION"] = (
        "NO_BLACKLISTING_DECLARATION"
    )
    source_file: str
    fields: NoBlacklistingDeclarationFields


NormalizedDocument = (
    PanRecordDocument
    | OemAuthorizationDocument
    | ProductDatasheetDocument
    | GstRegistrationDocument
    | UdyamRegistrationDocument
    | EpfoRegistrationDocument
    | EpfoContributionStatusDocument
    | EsicRegistrationDocument
    | EsicContributionStatusDocument
    | TurnoverCertificateDocument
    | AuditedFinancialsDocument
    | SimilarExperienceDocument
    | LocalContentDocument
    | TechnicalComplianceMatrixDocument
    | WarrantySlaUndertakingDocument
    | EmdEvidenceDocument
    | FinancialBoqDocument
    | NoBlacklistingDeclarationDocument
)
