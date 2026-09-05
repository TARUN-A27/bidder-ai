from __future__ import annotations

import hashlib
import json
import shutil
import stat
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from fastapi import UploadFile
from pydantic import ValidationError
from pypdf import PdfReader

from app.core.config import Settings
from app.schemas.submission_ingestion import (
    BidderImportMetadata,
    SubmissionManifestInput,
)
from app.services.ingestion.errors import (
    IngestionMetadataError,
    InvalidPdfError,
    InvalidSubmissionArchiveError,
    UnsafeArchivePathError,
    UnsupportedFileTypeError,
)


CHUNK_SIZE = 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024
MAX_PATH_DEPTH = 20
MAX_PATH_LENGTH = 1000
APPROVED_METADATA = {"bidder_profile.json", "document_manifest.json"}


@dataclass(frozen=True, slots=True)
class CollectedPackageDocument:
    original_path: str
    filename: str
    local_path: Path
    size_bytes: int
    sha256: str
    page_count: int


@dataclass(slots=True)
class CollectedPackage:
    root: Path
    payload_root: Path
    bidder: BidderImportMetadata
    manifest: SubmissionManifestInput | None
    documents: list[CollectedPackageDocument]

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class SubmissionPackageCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def collect_zip(
        self,
        upload: UploadFile,
        metadata_override: str | None = None,
    ) -> CollectedPackage:
        if Path(upload.filename or "").suffix.casefold() != ".zip":
            raise InvalidSubmissionArchiveError("A .zip archive is required")
        root = self._new_root()
        archive_path = root / "package.zip"
        try:
            await self._write_upload(upload, archive_path, self.settings.max_archive_bytes)
            if not zipfile.is_zipfile(archive_path):
                raise InvalidSubmissionArchiveError("The upload is not a valid ZIP archive")
            package = self._extract(root, archive_path, metadata_override)
            archive_path.unlink(missing_ok=True)
            return package
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise

    async def collect_files(
        self,
        uploads: list[UploadFile],
        bidder_profile: str,
        document_manifest: str | None = None,
    ) -> CollectedPackage:
        if not uploads:
            raise UnsupportedFileTypeError("At least one PDF is required")
        if len(uploads) > self.settings.max_upload_files:
            raise UnsupportedFileTypeError("The package contains too many files")
        root = self._new_root()
        payload_root = root / "payload"
        payload_root.mkdir()
        seen_names: set[str] = set()
        documents: list[CollectedPackageDocument] = []
        total_size = 0
        try:
            for upload in uploads:
                relative = self._safe_relative_path(upload.filename or "")
                filename = self._pdf_filename(relative)
                self._claim_filename(filename, seen_names)
                destination = payload_root / filename
                size, digest = await self._write_upload(
                    upload, destination, self.settings.max_pdf_bytes
                )
                total_size += size
                self._check_total_size(total_size)
                page_count = self._validate_pdf(destination, filename)
                documents.append(CollectedPackageDocument(
                    original_path=relative, filename=filename,
                    local_path=destination, size_bytes=size,
                    sha256=digest, page_count=page_count,
                ))
            bidder = parse_bidder_metadata(self._load_json_text(bidder_profile, "bidder_profile"))
            manifest = (
                parse_manifest(self._load_json_text(document_manifest, "document_manifest"))
                if document_manifest else None
            )
            documents.sort(key=lambda item: item.filename.casefold())
            return CollectedPackage(root, payload_root, bidder, manifest, documents)
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise

    def _extract(
        self,
        root: Path,
        archive_path: Path,
        metadata_override: str | None,
    ) -> CollectedPackage:
        payload_root = root / "payload"
        payload_root.mkdir()
        metadata: dict[str, dict] = {}
        documents: list[CollectedPackageDocument] = []
        seen_names: set[str] = set()
        total_size = 0
        with zipfile.ZipFile(archive_path) as archive:
            entries: list[tuple[zipfile.ZipInfo, str, str]] = []
            for info in archive.infolist():
                relative = self._safe_relative_path(info.filename, directory=info.is_dir())
                self._validate_zip_metadata(info)
                if info.is_dir():
                    continue
                basename = PurePosixPath(relative).name
                lower = basename.casefold()
                suffix = PurePosixPath(basename).suffix.casefold()
                if suffix == ".json":
                    if lower not in APPROVED_METADATA:
                        raise UnsupportedFileTypeError(
                            f"Unsupported metadata file: {basename}"
                        )
                    if lower in metadata:
                        raise IngestionMetadataError(f"Duplicate metadata file: {basename}")
                    if info.file_size > MAX_METADATA_BYTES:
                        raise IngestionMetadataError(f"Metadata file is too large: {basename}")
                    metadata[lower] = self._read_json_entry(archive, info, basename)
                    continue
                if suffix != ".pdf":
                    raise UnsupportedFileTypeError(f"Only PDFs and approved metadata are allowed: {basename}")
                filename = self._pdf_filename(relative)
                self._claim_filename(filename, seen_names)
                if len(entries) >= self.settings.max_upload_files:
                    raise UnsupportedFileTypeError("The package contains too many PDFs")
                if info.file_size > self.settings.max_pdf_bytes:
                    raise UnsupportedFileTypeError(f"PDF exceeds the configured size limit: {filename}")
                total_size += info.file_size
                self._check_total_size(total_size)
                if info.file_size and (
                    info.compress_size == 0
                    or info.file_size / info.compress_size > self.settings.max_zip_compression_ratio
                ):
                    raise InvalidSubmissionArchiveError("ZIP entry has an unsafe compression ratio")
                entries.append((info, relative, filename))
            if not entries:
                raise UnsupportedFileTypeError("The package does not contain any PDFs")

            for info, relative, filename in entries:
                destination = payload_root / filename
                digest = hashlib.sha256()
                written = 0
                with archive.open(info) as source, destination.open("xb") as target:
                    while chunk := source.read(CHUNK_SIZE):
                        written += len(chunk)
                        if written > self.settings.max_pdf_bytes:
                            raise UnsupportedFileTypeError(f"PDF exceeds the configured size limit: {filename}")
                        digest.update(chunk)
                        target.write(chunk)
                if written != info.file_size:
                    raise InvalidSubmissionArchiveError(f"ZIP entry size mismatch: {filename}")
                documents.append(CollectedPackageDocument(
                    original_path=relative, filename=filename,
                    local_path=destination, size_bytes=written,
                    sha256=digest.hexdigest(),
                    page_count=self._validate_pdf(destination, filename),
                ))

        profile_payload = (
            self._load_json_text(metadata_override, "bidder metadata")
            if metadata_override else metadata.get("bidder_profile.json")
        )
        if profile_payload is None:
            raise IngestionMetadataError("bidder_profile.json or bidder metadata is required")
        bidder = parse_bidder_metadata(profile_payload)
        manifest_payload = metadata.get("document_manifest.json")
        manifest = parse_manifest(manifest_payload) if manifest_payload is not None else None
        documents.sort(key=lambda item: item.filename.casefold())
        return CollectedPackage(root, payload_root, bidder, manifest, documents)

    def _new_root(self) -> Path:
        root = self.settings.storage_root / ".staging" / str(uuid.uuid4())
        root.mkdir(parents=True, exist_ok=False)
        return root.resolve()

    @staticmethod
    async def _write_upload(upload: UploadFile, destination: Path, limit: int) -> tuple[int, str]:
        digest = hashlib.sha256()
        written = 0
        with destination.open("xb") as target:
            while chunk := await upload.read(CHUNK_SIZE):
                written += len(chunk)
                if written > limit:
                    raise UnsupportedFileTypeError("Uploaded file exceeds the configured size limit")
                digest.update(chunk)
                target.write(chunk)
        return written, digest.hexdigest()

    @staticmethod
    def _safe_relative_path(raw: str, directory: bool = False) -> str:
        candidate = raw[:-1] if directory and raw.endswith("/") else raw
        if not candidate or "\x00" in candidate or "\\" in candidate:
            raise UnsafeArchivePathError("Archive or file path is unsafe")
        normalized = unicodedata.normalize("NFC", candidate)
        path = PurePosixPath(normalized)
        parts = path.parts
        if (path.is_absolute() or normalized.startswith("/") or not parts
                or any(part in {"", ".", ".."} for part in parts)
                or ":" in parts[0] or len(parts) > MAX_PATH_DEPTH
                or len(normalized) > MAX_PATH_LENGTH
                or "/".join(parts) != normalized):
            raise UnsafeArchivePathError("Archive or file path is unsafe")
        return normalized

    @staticmethod
    def _pdf_filename(relative: str) -> str:
        filename = PurePosixPath(relative).name
        if PurePosixPath(filename).suffix.casefold() != ".pdf":
            raise UnsupportedFileTypeError(f"Only PDF documents are allowed: {filename}")
        return filename

    @staticmethod
    def _claim_filename(filename: str, seen: set[str]) -> None:
        identity = unicodedata.normalize("NFC", filename).casefold()
        if identity in seen:
            raise UnsupportedFileTypeError(f"Duplicate PDF filename: {filename}")
        seen.add(identity)

    @staticmethod
    def _validate_zip_metadata(info: zipfile.ZipInfo) -> None:
        if info.flag_bits & 0x1:
            raise InvalidSubmissionArchiveError("Encrypted ZIP entries are not allowed")
        mode = info.external_attr >> 16
        if mode and stat.S_ISLNK(mode):
            raise InvalidSubmissionArchiveError("ZIP symbolic links are not allowed")

    @staticmethod
    def _read_json_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo, name: str) -> dict:
        try:
            with archive.open(info) as source:
                raw = source.read(MAX_METADATA_BYTES + 1)
            if len(raw) > MAX_METADATA_BYTES:
                raise IngestionMetadataError(f"Metadata file is too large: {name}")
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IngestionMetadataError(f"Invalid JSON metadata: {name}") from exc
        if not isinstance(value, dict):
            raise IngestionMetadataError(f"Metadata must be a JSON object: {name}")
        return value

    @staticmethod
    def _load_json_text(raw: str | None, name: str) -> dict:
        if raw is None or len(raw.encode("utf-8")) > MAX_METADATA_BYTES:
            raise IngestionMetadataError(f"Invalid or oversized {name}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IngestionMetadataError(f"Invalid JSON in {name}") from exc
        if not isinstance(value, dict):
            raise IngestionMetadataError(f"{name} must be a JSON object")
        return value

    def _check_total_size(self, total: int) -> None:
        if total > self.settings.max_total_pdf_bytes:
            raise UnsupportedFileTypeError("Combined PDF size exceeds the configured limit")

    @staticmethod
    def _validate_pdf(path: Path, filename: str) -> int:
        with path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise InvalidPdfError(f"File does not have a PDF header: {filename}")
        try:
            reader = PdfReader(str(path), strict=False)
            if reader.is_encrypted:
                raise InvalidPdfError(f"Encrypted PDFs are not supported: {filename}")
            pages = len(reader.pages)
        except InvalidPdfError:
            raise
        except Exception as exc:
            raise InvalidPdfError(f"File is not a readable PDF: {filename}") from exc
        if pages < 1:
            raise InvalidPdfError(f"PDF has no pages: {filename}")
        return pages


def parse_bidder_metadata(raw: dict) -> BidderImportMetadata:
    try:
        if "bidder_identity" not in raw:
            return BidderImportMetadata.model_validate(raw)
        identity = raw.get("bidder_identity")
        claims = raw.get("claims")
        product = raw.get("offered_product")
        if not all(isinstance(value, dict) for value in (identity, claims, product)):
            raise IngestionMetadataError("Bidder profile sections are missing or invalid")
        return BidderImportMetadata(
            dataset_id=raw.get("dataset_id"),
            bidder_reference=identity.get("bidder_id"),
            bidder_name=identity.get("legal_name"),
            entity_type=identity.get("entity_type"),
            registered_address=identity.get("registered_address"),
            pan_reference=identity.get("pan"),
            gst_reference=identity.get("gstin"),
            udyam_reference=identity.get("udyam"),
            is_synthetic=True,
            mse_claimed=claims.get("mse_purchase_preference", False),
            startup_claimed=claims.get("startup_turnover_relaxation", False),
            nsic_claimed=claims.get("nsic_related_benefit", bool(identity.get("nsic_spr"))),
            emd_exemption_claimed=claims.get("emd_exemption", False),
            offered_make=product.get("brand"),
            offered_model=product.get("model"),
        )
    except ValidationError as exc:
        raise IngestionMetadataError("Bidder metadata is missing required identity fields") from exc


def parse_manifest(raw: dict) -> SubmissionManifestInput:
    try:
        return SubmissionManifestInput.model_validate(raw)
    except ValidationError as exc:
        raise IngestionMetadataError("Document manifest is invalid") from exc
