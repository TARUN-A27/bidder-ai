from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class VerificationSourceEvidence(BaseModel):
    source_key: str
    source_system: str
    source_snapshot_at: datetime | None = None
    verification_status: str | None = None
    record_classification: str | None = None
    synthetic: bool | None = None


class GstReturnEvidence(BaseModel):
    period: str
    gstr1_status: str | None = None
    gstr1_filed_on: date | None = None
    gstr3b_status: str | None = None
    gstr3b_filed_on: date | None = None


class GstRegistryEvidence(VerificationSourceEvidence):
    gstin: str | None = None
    legal_name: str | None = None
    pan_reference: str | None = None
    status: str | None = None
    effective_date: date | None = None
    cancellation_date: date | None = None
    status_at_bid_close: str | None = None
    latest_return_period: str | None = None
    missing_return_periods: list[str] = Field(default_factory=list)
    returns: list[GstReturnEvidence] = Field(default_factory=list)


class PanRegistryEvidence(VerificationSourceEvidence):
    pan_reference: str | None = None
    legal_name: str | None = None
    entity_type: str | None = None
    status: str | None = None
    incorporation_date: date | None = None
    identity_match: str | None = None
    uploaded_pan_reference: str | None = None
    uploaded_legal_name: str | None = None


class UdyamRegistryEvidence(VerificationSourceEvidence):
    udyam_number: str | None = None
    enterprise_name: str | None = None
    pan_reference: str | None = None
    classification: str | None = None
    status: str | None = None
    relevant_activity: bool | None = None
    activities: list[str] = Field(default_factory=list)


class EpfoRegistryEvidence(VerificationSourceEvidence):
    establishment_code: str | None = None
    establishment_name: str | None = None
    pan_reference: str | None = None
    registration_status: str | None = None
    contribution_state: str | None = None
    compliant_through: str | None = None
    latest_due_period: str | None = None
    latest_period: str | None = None
    payment_status: str | None = None
    payment_date: date | None = None
    due_date: date | None = None
    outstanding_amount: Decimal | None = None
    portal_document_match: bool | None = None


class EsicRegistryEvidence(VerificationSourceEvidence):
    employer_code: str | None = None
    employer_name: str | None = None
    pan_reference: str | None = None
    registration_status: str | None = None
    status_at_bid_close: str | None = None
    contribution_state: str | None = None
    compliant_through: str | None = None
    latest_period: str | None = None
    payment_date: date | None = None
    outstanding_amount: Decimal | None = None
    default_reason: str | None = None


class DpiitRegistryEvidence(VerificationSourceEvidence):
    claim_submitted: bool | None = None
    applicability: str | None = None
    reason: str | None = None
    recognition_number: str | None = None
    entity_name: str | None = None
    pan_reference: str | None = None
    entity_type: str | None = None
    recognition_date: date | None = None
    valid_through: date | None = None
    status: str | None = None
    identity_match: str | None = None
    claim_submitted_on: date | None = None
    claim_before_bid_deadline: bool | None = None
    tender_permits_relaxation: bool | None = None
    relaxed_requirement_ids: list[str] = Field(default_factory=list)
    automatic_exemption_assumed: bool | None = None


class NsicRegistryEvidence(VerificationSourceEvidence):
    claim_submitted: bool | None = None
    applicability: str | None = None
    reason: str | None = None
    registration_number: str | None = None
    entity_name: str | None = None
    pan_reference: str | None = None
    status: str | None = None
    valid_from: date | None = None
    valid_through: date | None = None
    covered_categories: list[str] = Field(default_factory=list)
    tender_category_relevant: bool | None = None
    automatic_benefit_assumed: bool | None = None


class DebarmentRegistryEvidence(VerificationSourceEvidence):
    entity_name: str | None = None
    pan_reference: str | None = None
    active: bool | None = None
    status: str | None = None
    effective_from: date | None = None
    valid_through: date | None = None
    order_reference: str | None = None
    searched_through: datetime | None = None
    uploaded_self_declaration: str | None = None


class OemAuthorizationRegistryEvidence(VerificationSourceEvidence):
    authorization_number: str | None = None
    oem_name: str | None = None
    oem_registry_id: str | None = None
    authorized_bidder: str | None = None
    bidder_pan: str | None = None
    bid_number: str | None = None
    brand: str | None = None
    offered_model: str | None = None
    status: str | None = None
    document_present: bool | None = None
    issue_date: date | None = None
    valid_through: date | None = None
    tender_required_through: date | None = None
    status_at_bid_close: str | None = None
    validity_shortfall_days: int | None = None


class ProductCertificationRegistryEvidence(VerificationSourceEvidence):
    certificate_type: str | None = None
    certificate_number: str | None = None
    certificate_standard: str | None = None
    status: str | None = None
    certificate_holder: str | None = None
    manufacturer: str | None = None
    covered_models: list[str] = Field(default_factory=list)
    report_number: str | None = None
    valid_from: date | None = None
    valid_through: date | None = None
    exact_model_match: bool | None = None
    certificate_report_match: bool | None = None


class ProductDatasheetRegistryEvidence(VerificationSourceEvidence):
    oem_name: str | None = None
    oem_registry_id: str | None = None
    brand: str | None = None
    model: str | None = None
    product_family: str | None = None
    sku: str | None = None
    lifecycle_status: str | None = None
    technical_specifications: dict[str, str] = Field(default_factory=dict)
    failed_technical_requirements: list[str] = Field(default_factory=list)


class LocalContentVerificationEvidence(VerificationSourceEvidence):
    entity_name: str | None = None
    oem_name: str | None = None
    brand: str | None = None
    offered_model: str | None = None
    declared_local_content_percentage: float | None = None
    verified_local_content_percentage: float | None = None


class IssuerVerifiedExperienceRecord(BaseModel):
    work_order_number: str | None = None
    issuer: str | None = None
    scope: str | None = None
    value: Decimal | None = None
    start_date: date | None = None
    completion_date: date | None = None
    completion_status: str | None = None
    verification_reference: str | None = None


class IssuerVerificationEvidence(VerificationSourceEvidence):
    entity_name: str | None = None
    experience_years: float | None = None
    records: list[IssuerVerifiedExperienceRecord] = Field(default_factory=list)


class EmdVerificationEvidence(VerificationSourceEvidence):
    evidence_type: Literal["PAYMENT", "EXEMPTION"]
    entity_name: str | None = None
    pan_reference: str | None = None
    bid_number: str | None = None
    amount: Decimal | None = None
    payment_reference: str | None = None
    payment_status: str | None = None
    payment_date: date | None = None
    bid_deadline: datetime | None = None
    paid_before_bid_deadline: bool | None = None
    payment_reference_valid: bool | None = None
    bid_number_match: bool | None = None
    bidder_identity_match: bool | None = None
    exemption_claimed: bool | None = None
    claim_submitted_on: date | None = None
    tender_permits_exemption: bool | None = None
    udyam_valid: bool | None = None
    nsic_valid: bool | None = None
    nsic_category_relevant: bool | None = None
    automatic_benefit_assumed: bool | None = None
    final_acceptance_authority: str | None = None


class VerificationEvidenceBundle(BaseModel):
    dataset_id: str
    bidder_id: str
    canonical_identity_reference: str
    snapshot_at: datetime
    data_classification: str | None = None
    disclaimer: str | None = None
    synthetic: bool = True
    gst: GstRegistryEvidence | None = None
    pan: PanRegistryEvidence | None = None
    udyam: UdyamRegistryEvidence | None = None
    epfo: EpfoRegistryEvidence | None = None
    esic: EsicRegistryEvidence | None = None
    dpiit: DpiitRegistryEvidence | None = None
    nsic: NsicRegistryEvidence | None = None
    debarment: DebarmentRegistryEvidence | None = None
    oem_authorization: OemAuthorizationRegistryEvidence | None = None
    product_certification: ProductCertificationRegistryEvidence | None = None
    product_datasheet: ProductDatasheetRegistryEvidence | None = None
    local_content: LocalContentVerificationEvidence | None = None
    issuer_verification: IssuerVerificationEvidence | None = None
    emd: EmdVerificationEvidence | None = None
    unknown_sources: dict[str, Any] = Field(default_factory=dict)
