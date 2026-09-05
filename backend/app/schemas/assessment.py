from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.compliance import RequirementEvaluationResult
from app.schemas.scoring import BidAssessmentResult


class SubmissionResponse(BaseModel):
    submission_id: str
    tender_id: str
    bidder_id: str
    bidder_name: str
    pan_reference: str | None = None
    dataset_id: str | None = None
    bid_number: str
    status: str | None = None
    offered_model: str | None = None
    mse_claimed: bool
    startup_claimed: bool
    nsic_claimed: bool
    emd_exemption_claimed: bool
    assessment_available: bool = False
    score: float | None = None
    final_risk: str | None = None


class PersistedRequirementResult(RequirementEvaluationResult):
    title: str
    configured_weight: float
    awarded_points: float


class AssessmentSummaryResponse(BidAssessmentResult):
    submission_id: str
    bidder_id: str
    bidder_name: str
    tender_id: str
    assessed_at: datetime
    requirement_results: list[PersistedRequirementResult]
    advisory: bool = True


class TenderResponse(BaseModel):
    tender_id: str
    dataset_id: str | None = None
    bid_number: str
    title: str
    buyer: str | None = None
    closing_date: datetime | None = None
    submission_count: int


class TenderRequirementResponse(BaseModel):
    requirement_code: str
    title: str
    description: str | None = None
    weight: float
    severity: str
    applicability: str | None = None


class TechnicalRequirementResponse(BaseModel):
    technical_code: str
    parameter_name: str
    minimum_requirement: str
    classification: str | None = None


class RequiredDocumentResponse(BaseModel):
    document_code: str
    document_name: str
    mandatory: bool
    conditional: bool
    condition_text: str | None = None


class TenderDetailResponse(TenderResponse):
    requirements: list[TenderRequirementResponse]
    technical_requirements: list[TechnicalRequirementResponse]
    mandatory_documents: list[RequiredDocumentResponse]


class ComparisonBidder(BaseModel):
    submission_id: str
    bidder_name: str
    score: float
    final_risk: str
    recommendation: str
    non_compliant_count: int
    missing_count: int
    needs_review_count: int


class ComparisonResponse(BaseModel):
    tender_id: str
    bidders: list[ComparisonBidder] = Field(default_factory=list)
