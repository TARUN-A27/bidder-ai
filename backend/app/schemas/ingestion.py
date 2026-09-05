from __future__ import annotations

from pydantic import BaseModel


class IngestedDocumentResponse(BaseModel):
    id: str
    relative_path: str
    file_name: str
    storage_path: str
    sha256: str
    page_count: int
    upload_status: str


class SubmissionIngestionResponse(BaseModel):
    submission_id: str
    document_count: int
    documents: list[IngestedDocumentResponse]
