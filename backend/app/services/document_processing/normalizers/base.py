from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.document_extraction import (
    DocumentExtractionResult,
    ExtractedTable,
)


class DocumentNormalizationError(Exception):
    """Base exception for document normalization failures."""


def normalize_whitespace(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalized.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def canonicalize_label(value: str | None) -> str:
    normalized = normalize_whitespace(value).casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return normalize_whitespace(normalized)


def clean_extracted_value(value: str | None) -> str | None:
    cleaned = normalize_whitespace(value)
    cleaned = cleaned.strip(" \t\r\n:：|–—")
    return cleaned or None


def parse_date_value(value: str | None) -> date | None:
    if not value:
        return None

    normalized = normalize_whitespace(value)
    normalized = re.sub(
        r"(\d{1,2})(st|nd|rd|th)\b",
        r"\1",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = normalized.replace(",", " ")

    patterns = (
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        r"\b\d{4}/\d{1,2}/\d{1,2}\b",
    )
    formats = (
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    )

    candidates: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            candidates.append(match.group(0))

    if not candidates:
        candidates.append(normalized)

    for candidate in candidates:
        for date_format in formats:
            try:
                return datetime.strptime(candidate.title(), date_format).date()
            except ValueError:
                continue

    return None


def extract_integer(value: str | None) -> int | None:
    if not value:
        return None

    match = re.search(r"(?<!\w)(\d[\d,]*)", value)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def parse_currency_amount(value: str | None) -> Decimal | None:
    if not value:
        return None

    match = re.search(
        r"(?:INR|₹)?\s*(-?\d[\d,]*(?:\.\d+)?)",
        normalize_whitespace(value),
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    try:
        amount = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None

    canonical_value = canonicalize_label(value)
    if "crore" in canonical_value.split():
        amount *= Decimal("10000000")
    elif "lakh" in canonical_value.split():
        amount *= Decimal("100000")
    return amount


def parse_percentage_value(value: str | None) -> float | None:
    if not value:
        return None

    match = re.search(
        r"(-?\d+(?:\.\d+)?)\s*(?:%|percent\b)",
        normalize_whitespace(value),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return float(match.group(1))


def table_rows(table: ExtractedTable) -> list[dict[int, str]]:
    grouped_rows: dict[int, dict[int, str]] = defaultdict(dict)
    for cell in table.cells:
        cleaned = clean_extracted_value(cell.content)
        if cleaned:
            grouped_rows[cell.row_index][cell.column_index] = cleaned
    return [grouped_rows[row_index] for row_index in sorted(grouped_rows)]


def table_label_values(table: ExtractedTable) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in table_rows(table):
        label = canonicalize_label(row.get(0))
        value = row.get(1)
        if label and value and label not in values:
            values[label] = value
    return values


def find_table_row(
    extraction: DocumentExtractionResult,
    first_column_value: str | None,
) -> dict[int, str]:
    expected = canonicalize_label(first_column_value)
    if not expected:
        return {}

    for table in extraction.tables:
        for row in table_rows(table):
            if canonicalize_label(row.get(0)) == expected:
                return row

    return {}


def extract_integer_before_unit(
    value: str | None,
    *units: str,
) -> int | None:
    if not value:
        return None

    escaped_units = "|".join(re.escape(unit) for unit in units)
    match = re.search(
        rf"(\d[\d,]*)\s*(?:{escaped_units})\b",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def parse_dimensions_mm(
    value: str | None,
) -> tuple[int | None, int | None]:
    if not value:
        return None, None

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm\b",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None

    return int(float(match.group(1))), int(float(match.group(2)))


def split_list_value(value: str | None) -> list[str]:
    if not value:
        return []

    normalized_values: list[str] = []
    seen: set[str] = set()
    for item in re.split(r"[,;•]+", value):
        cleaned = clean_extracted_value(item)
        if not cleaned:
            continue
        identity = cleaned.casefold()
        if identity not in seen:
            normalized_values.append(cleaned)
            seen.add(identity)
    return normalized_values


def normalize_decision(value: str | None) -> str | None:
    cleaned = clean_extracted_value(value)
    if not cleaned:
        return None

    upper = cleaned.upper()
    canonical_values = (
        "NOT APPLICABLE",
        "NOT AUTHORIZED",
        "EXACT MATCH",
        "MISMATCH",
        "CONFIRMED",
        "AUTHORIZED",
        "INVALID",
        "VALID",
        "ACTIVE",
        "INACTIVE",
        "YES",
        "NO",
    )
    for canonical_value in canonical_values:
        if upper == canonical_value or canonical_value in upper:
            return canonical_value
    return upper


class EvidenceLookup:
    """Find known label/value evidence in tables and text lines."""

    _explicit_pair_pattern = re.compile(
        r"^\s*(.{2,100}?)\s*[:：]\s*(.+?)\s*$"
    )
    _noise_patterns = (
        re.compile(r"synthetic\s+test\s+document", re.IGNORECASE),
        re.compile(r"not\s+valid\s+for\s+official\s+use", re.IGNORECASE),
        re.compile(r"^\s*page\s+\d+(?:\s+of\s+\d+)?\s*$", re.IGNORECASE),
        re.compile(r"^\s*confidential\s*$", re.IGNORECASE),
    )

    def __init__(
        self,
        extraction: DocumentExtractionResult,
        known_labels: list[str],
    ) -> None:
        self.extraction = extraction
        self.known_labels = {
            canonicalize_label(label)
            for label in known_labels
            if canonicalize_label(label)
        }
        self.lines = self._collect_lines()
        self.table_pairs = self._collect_table_pairs()

    def find_value(self, aliases: tuple[str, ...]) -> str | None:
        canonical_aliases = sorted(
            {
                canonicalize_label(alias)
                for alias in aliases
                if canonicalize_label(alias)
            },
            key=len,
            reverse=True,
        )

        for label, value in self.table_pairs:
            if self._matches_any_label(label, canonical_aliases):
                cleaned = clean_extracted_value(value)
                if self._is_usable_value(cleaned):
                    return cleaned

        for line_index, line in enumerate(self.lines):
            explicit_pair = self._split_explicit_pair(line)
            if explicit_pair:
                label, value = explicit_pair
                if self._matches_any_label(label, canonical_aliases):
                    cleaned = clean_extracted_value(value)
                    if self._is_usable_value(cleaned):
                        return cleaned

            for alias in canonical_aliases:
                inline_value = self._extract_inline_value(line, alias)
                if self._is_usable_value(inline_value):
                    return inline_value

            if self._matches_any_label(line, canonical_aliases):
                following_value = self._next_text_value(line_index)
                if following_value:
                    return following_value

        return None

    def _collect_lines(self) -> list[str]:
        lines: list[str] = []
        if self.extraction.pages:
            for page in self.extraction.pages:
                lines.extend(page.lines)
        else:
            lines.extend(self.extraction.content.splitlines())
        return [
            normalized
            for line in lines
            if (normalized := normalize_whitespace(line))
        ]

    def _collect_table_pairs(self) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for table in self.extraction.tables:
            rows: dict[int, list[Any]] = defaultdict(list)
            for cell in table.cells:
                rows[cell.row_index].append(cell)

            for row_index in sorted(rows):
                cells_by_column = {
                    cell.column_index: cell
                    for cell in rows[row_index]
                }

                for column_index in sorted(cells_by_column):
                    cell = cells_by_column[column_index]
                    explicit_pair = self._split_explicit_pair(cell.content)
                    if (
                        explicit_pair
                        and canonicalize_label(explicit_pair[0])
                        in self.known_labels
                    ):
                        pairs.append(explicit_pair)

                    label = clean_extracted_value(cell.content)
                    value_cell = cells_by_column.get(column_index + 1)
                    value = (
                        clean_extracted_value(value_cell.content)
                        if value_cell is not None
                        else None
                    )
                    if (
                        label
                        and value
                        and canonicalize_label(label) in self.known_labels
                    ):
                        pairs.append((label, value))
        return pairs

    @classmethod
    def _split_explicit_pair(
        cls,
        value: str,
    ) -> tuple[str, str] | None:
        normalized = normalize_whitespace(value)
        if not normalized:
            return None

        match = cls._explicit_pair_pattern.match(normalized)
        if match:
            return match.group(1), match.group(2)

        if "\n" in value:
            parts = [
                normalize_whitespace(part)
                for part in value.splitlines()
                if normalize_whitespace(part)
            ]
            if len(parts) >= 2:
                return parts[0], " ".join(parts[1:])
        return None

    @staticmethod
    def _labels_match(candidate: str, expected: str) -> bool:
        return canonicalize_label(candidate) == expected

    def _matches_any_label(
        self,
        candidate: str,
        aliases: list[str],
    ) -> bool:
        return any(self._labels_match(candidate, alias) for alias in aliases)

    @staticmethod
    def _extract_inline_value(
        line: str,
        canonical_alias: str,
    ) -> str | None:
        words = canonical_alias.split()
        if not words:
            return None

        label_pattern = r"[\s\W_]+".join(re.escape(word) for word in words)
        match = re.match(
            rf"^\s*{label_pattern}"
            rf"(?:\s*[:：\-–—]\s*|\s+)"
            rf"(.+?)\s*$",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        return clean_extracted_value(match.group(1))

    def _next_text_value(self, line_index: int) -> str | None:
        for candidate in self.lines[line_index + 1 : line_index + 7]:
            cleaned = clean_extracted_value(candidate)
            if self._is_usable_value(cleaned):
                return cleaned
        return None

    def _is_usable_value(self, value: str | None) -> bool:
        if not value or not re.search(r"[A-Za-z0-9]", value):
            return False
        if any(pattern.search(value) for pattern in self._noise_patterns):
            return False

        canonical_value = canonicalize_label(value)
        if canonical_value in self.known_labels:
            return False

        explicit_pair = self._split_explicit_pair(value)
        if (
            explicit_pair
            and canonicalize_label(explicit_pair[0]) in self.known_labels
        ):
            return False
        return True


class BaseDocumentNormalizer(ABC):
    document_type: str
    field_aliases: dict[str, tuple[str, ...]]

    def __init__(self, extraction: DocumentExtractionResult) -> None:
        self.extraction = extraction
        known_labels = [
            alias
            for aliases in self.field_aliases.values()
            for alias in aliases
        ]
        self.evidence = EvidenceLookup(extraction, known_labels)

    def value(self, field_name: str) -> str | None:
        aliases = self.field_aliases.get(field_name)
        if aliases is None:
            raise DocumentNormalizationError(
                f"Unknown normalization field: {field_name}"
            )
        return self.evidence.find_value(aliases)

    @abstractmethod
    def normalize(self) -> Any:
        """Return the document-specific normalized model."""
