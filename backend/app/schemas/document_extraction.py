from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedPage(BaseModel):
    page_number: int = Field(ge=1)
    line_count: int = Field(ge=0)
    lines: list[str] = Field(default_factory=list)


class ExtractedTableCell(BaseModel):
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    content: str = ""


class ExtractedTable(BaseModel):
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    cells: list[ExtractedTableCell] = Field(default_factory=list)


class ExtractionMetadata(BaseModel):
    content_length: int = Field(ge=0)
    source_path: str


class DocumentExtractionResult(BaseModel):
    file_name: str
    model_id: str
    page_count: int = Field(ge=0)
    table_count: int = Field(ge=0)
    content: str
    pages: list[ExtractedPage] = Field(default_factory=list)
    tables: list[ExtractedTable] = Field(default_factory=list)
    metadata: ExtractionMetadata
