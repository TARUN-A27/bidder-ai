from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BidderDocumentCreate:
    id: str
    submission_id: str
    relative_path: str
    file_name: str
    storage_path: str
    sha256: str
    page_count: int
    document_code: str | None = None
    document_type: str | None = None
    classification_confidence: float | None = None
    upload_status: str = "UPLOADED"
