from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BidderImportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str | None = None
    bidder_reference: str | None = None
    bidder_name: str
    entity_type: str | None = None
    registered_address: str | None = None
    pan_reference: str
    gst_reference: str | None = None
    udyam_reference: str | None = None
    is_synthetic: bool = False
    mse_claimed: bool = False
    startup_claimed: bool = False
    nsic_claimed: bool = False
    emd_exemption_claimed: bool = False
    offered_make: str | None = None
    offered_model: str | None = None


class ManifestDocumentInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_number: str | None = None
    file_name: str
    page_count: int | None = Field(default=None, ge=1)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")


class SubmissionManifestInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dataset_id: str | None = None
    bidder_id: str
    bidder_name: str
    document_count: int = Field(ge=1)
    documents: list[ManifestDocumentInput]


class IngestedSubmissionDocument(BaseModel):
    document_id: str
    document_code: str | None = None
    document_type: str
    filename: str
    normalized_filename: str
    sha256: str
    size_bytes: int
    page_count: int
    processing_status: str


class SubmissionIngestionResponse(BaseModel):
    submission_id: str
    bidder_id: str
    bidder_name: str
    tender_id: str
    document_count: int
    documents: list[IngestedSubmissionDocument]
    warnings: list[str] = Field(default_factory=list)
    status: str
    ready_for_assessment: bool
    duplicate_import: bool = False
