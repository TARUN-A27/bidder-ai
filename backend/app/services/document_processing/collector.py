from __future__ import annotations

import hashlib
import shutil
import stat
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from fastapi import UploadFile
from pypdf import PdfReader

from app.core.config import Settings
from app.core.errors import UploadValidationError


CHUNK_SIZE = 1024 * 1024
MAX_PATH_DEPTH = 20
MAX_RELATIVE_PATH_LENGTH = 1000


@dataclass(frozen=True, slots=True)
class CollectedDocument:
    relative_path: str
    local_path: Path
    size_bytes: int
    sha256: str
    page_count: int


@dataclass(slots=True)
class CollectedSubmission:
    root: Path
    documents: list[CollectedDocument]

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class SubmissionFileCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def collect_folder(
        self,
        submission_id: str,
        uploads: list[UploadFile],
    ) -> CollectedSubmission:
        if not uploads:
            raise UploadValidationError(
                "At least one PDF is required",
                code="EMPTY_SUBMISSION",
            )
        if len(uploads) > self.settings.max_upload_files:
            raise self._too_many_files()

        root = self._new_staging_root(submission_id)
        documents: list[CollectedDocument] = []
        seen_paths: set[str] = set()
        total_size = 0

        try:
            for upload in uploads:
                relative_path = self._validated_pdf_path(upload.filename)
                self._claim_path(relative_path, seen_paths)
                destination = self._safe_destination(root, relative_path)
                destination.parent.mkdir(parents=True, exist_ok=True)

                size, digest = await self._write_upload(
                    upload,
                    destination,
                    max_bytes=self.settings.max_pdf_bytes,
                )
                total_size += size
                if total_size > self.settings.max_total_pdf_bytes:
                    raise UploadValidationError(
                        "Combined PDF size exceeds the configured limit",
                        code="TOTAL_UPLOAD_TOO_LARGE",
                        status_code=413,
                    )

                page_count = self._validate_pdf(destination, relative_path)
                documents.append(
                    CollectedDocument(
                        relative_path=relative_path,
                        local_path=destination,
                        size_bytes=size,
                        sha256=digest,
                        page_count=page_count,
                    )
                )
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise

        documents.sort(key=lambda item: item.relative_path.casefold())
        return CollectedSubmission(root=root, documents=documents)

    async def collect_zip(
        self,
        submission_id: str,
        archive: UploadFile,
    ) -> CollectedSubmission:
        archive_name = archive.filename or ""
        if Path(archive_name).suffix.lower() != ".zip":
            raise UploadValidationError(
                "The uploaded archive must have a .zip extension",
                code="ZIP_REQUIRED",
            )

        root = self._new_staging_root(submission_id)
        archive_path = root / "_submission.zip"

        try:
            await self._write_upload(
                archive,
                archive_path,
                max_bytes=self.settings.max_archive_bytes,
            )
            if not zipfile.is_zipfile(archive_path):
                raise UploadValidationError(
                    "The uploaded file is not a valid ZIP archive",
                    code="INVALID_ZIP",
                )

            documents = self._extract_zip(archive_path, root)
            archive_path.unlink(missing_ok=True)
        except UploadValidationError:
            shutil.rmtree(root, ignore_errors=True)
            raise
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            shutil.rmtree(root, ignore_errors=True)
            raise UploadValidationError(
                "The ZIP archive could not be processed safely",
                code="INVALID_ZIP",
            ) from exc

        documents.sort(key=lambda item: item.relative_path.casefold())
        return CollectedSubmission(root=root, documents=documents)

    def _extract_zip(
        self,
        archive_path: Path,
        root: Path,
    ) -> list[CollectedDocument]:
        documents: list[CollectedDocument] = []
        seen_paths: set[str] = set()
        total_size = 0

        with zipfile.ZipFile(archive_path) as archive:
            file_entries: list[tuple[zipfile.ZipInfo, str]] = []

            for info in archive.infolist():
                relative_path = self._validated_archive_path(
                    info.filename,
                    is_directory=info.is_dir(),
                )
                self._reject_unsafe_zip_metadata(info)

                if info.is_dir():
                    continue

                relative_path = self._validated_pdf_path(relative_path)
                self._claim_path(relative_path, seen_paths)
                file_entries.append((info, relative_path))

                if len(file_entries) > self.settings.max_upload_files:
                    raise self._too_many_files()
                if info.file_size > self.settings.max_pdf_bytes:
                    raise UploadValidationError(
                        f"PDF exceeds the configured size limit: "
                        f"{relative_path}",
                        code="PDF_TOO_LARGE",
                        status_code=413,
                    )

                total_size += info.file_size
                if total_size > self.settings.max_total_pdf_bytes:
                    raise UploadValidationError(
                        "Combined uncompressed PDF size exceeds the "
                        "configured limit",
                        code="TOTAL_UPLOAD_TOO_LARGE",
                        status_code=413,
                    )
                if info.file_size:
                    if info.compress_size == 0:
                        raise UploadValidationError(
                            "ZIP entry has an unsafe compression ratio",
                            code="UNSAFE_ZIP_ENTRY",
                        )
                    ratio = info.file_size / info.compress_size
                    if ratio > self.settings.max_zip_compression_ratio:
                        raise UploadValidationError(
                            "ZIP entry has an unsafe compression ratio",
                            code="UNSAFE_ZIP_ENTRY",
                        )

            if not file_entries:
                raise UploadValidationError(
                    "The ZIP archive does not contain any PDFs",
                    code="EMPTY_SUBMISSION",
                )

            for info, relative_path in file_entries:
                destination = self._safe_destination(root, relative_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                written = 0

                with archive.open(info, "r") as source, destination.open(
                    "xb"
                ) as target:
                    while chunk := source.read(CHUNK_SIZE):
                        written += len(chunk)
                        if written > self.settings.max_pdf_bytes:
                            raise UploadValidationError(
                                f"PDF exceeds the configured size limit: "
                                f"{relative_path}",
                                code="PDF_TOO_LARGE",
                                status_code=413,
                            )
                        digest.update(chunk)
                        target.write(chunk)

                if written != info.file_size:
                    raise UploadValidationError(
                        f"ZIP entry size mismatch: {relative_path}",
                        code="INVALID_ZIP",
                    )

                page_count = self._validate_pdf(destination, relative_path)
                documents.append(
                    CollectedDocument(
                        relative_path=relative_path,
                        local_path=destination,
                        size_bytes=written,
                        sha256=digest.hexdigest(),
                        page_count=page_count,
                    )
                )

        return documents

    async def _write_upload(
        self,
        upload: UploadFile,
        destination: Path,
        *,
        max_bytes: int,
    ) -> tuple[int, str]:
        digest = hashlib.sha256()
        written = 0

        with destination.open("xb") as target:
            while chunk := await upload.read(CHUNK_SIZE):
                written += len(chunk)
                if written > max_bytes:
                    raise UploadValidationError(
                        "Uploaded file exceeds the configured size limit",
                        code="UPLOAD_TOO_LARGE",
                        status_code=413,
                    )
                digest.update(chunk)
                target.write(chunk)

        return written, digest.hexdigest()

    def _new_staging_root(self, submission_id: str) -> Path:
        root = (
            self.settings.storage_root
            / ".staging"
            / submission_id
            / str(uuid.uuid4())
        )
        root.mkdir(parents=True, exist_ok=False)
        return root.resolve()

    @staticmethod
    def _validated_archive_path(
        raw_path: str,
        *,
        is_directory: bool,
    ) -> str:
        candidate = (
            raw_path[:-1]
            if is_directory and raw_path.endswith("/")
            else raw_path
        )
        return SubmissionFileCollector._validated_relative_path(candidate)

    @staticmethod
    def _validated_pdf_path(raw_path: str | None) -> str:
        relative_path = SubmissionFileCollector._validated_relative_path(
            raw_path or ""
        )
        if PurePosixPath(relative_path).suffix.lower() != ".pdf":
            raise UploadValidationError(
                f"Only PDF documents are allowed: {relative_path}",
                code="PDF_ONLY",
            )
        return relative_path

    @staticmethod
    def _validated_relative_path(raw_path: str) -> str:
        if not raw_path or "\x00" in raw_path or "\\" in raw_path:
            raise UploadValidationError(
                "Archive or file path is unsafe",
                code="UNSAFE_PATH",
            )
        if raw_path.startswith("/") or "//" in raw_path:
            raise UploadValidationError(
                "Archive or file path is unsafe",
                code="UNSAFE_PATH",
            )

        normalized = unicodedata.normalize("NFC", raw_path)
        path = PurePosixPath(normalized)
        parts = path.parts

        if (
            path.is_absolute()
            or not parts
            or any(part in {"", ".", ".."} for part in parts)
            or ":" in parts[0]
            or len(parts) > MAX_PATH_DEPTH
            or len(normalized) > MAX_RELATIVE_PATH_LENGTH
        ):
            raise UploadValidationError(
                "Archive or file path is unsafe",
                code="UNSAFE_PATH",
            )

        canonical = "/".join(parts)
        if canonical != normalized:
            raise UploadValidationError(
                "Archive or file path is unsafe",
                code="UNSAFE_PATH",
            )
        return canonical

    @staticmethod
    def _safe_destination(root: Path, relative_path: str) -> Path:
        destination = (
            root / Path(*PurePosixPath(relative_path).parts)
        ).resolve()
        if not destination.is_relative_to(root):
            raise UploadValidationError(
                "Archive or file path escapes submission storage",
                code="UNSAFE_PATH",
            )
        return destination

    @staticmethod
    def _claim_path(relative_path: str, seen_paths: set[str]) -> None:
        identity = unicodedata.normalize("NFC", relative_path).casefold()
        if identity in seen_paths:
            raise UploadValidationError(
                f"Duplicate document path: {relative_path}",
                code="DUPLICATE_PATH",
            )
        seen_paths.add(identity)

    @staticmethod
    def _reject_unsafe_zip_metadata(info: zipfile.ZipInfo) -> None:
        if info.flag_bits & 0x1:
            raise UploadValidationError(
                "Encrypted ZIP entries are not allowed",
                code="UNSAFE_ZIP_ENTRY",
            )

        unix_mode = info.external_attr >> 16
        if unix_mode and stat.S_ISLNK(unix_mode):
            raise UploadValidationError(
                "Symbolic links are not allowed in ZIP archives",
                code="UNSAFE_ZIP_ENTRY",
            )

    @staticmethod
    def _validate_pdf(path: Path, relative_path: str) -> int:
        with path.open("rb") as source:
            header = source.read(1024)
        if b"%PDF-" not in header:
            raise UploadValidationError(
                f"File is not a valid PDF: {relative_path}",
                code="INVALID_PDF",
            )

        try:
            reader = PdfReader(str(path), strict=False)
            if reader.is_encrypted:
                raise UploadValidationError(
                    f"Encrypted PDFs are not supported: {relative_path}",
                    code="ENCRYPTED_PDF",
                )
            page_count = len(reader.pages)
        except UploadValidationError:
            raise
        except Exception as exc:
            raise UploadValidationError(
                f"File is not a readable PDF: {relative_path}",
                code="INVALID_PDF",
            ) from exc

        if page_count < 1:
            raise UploadValidationError(
                f"PDF has no pages: {relative_path}",
                code="INVALID_PDF",
            )
        return page_count

    def _too_many_files(self) -> UploadValidationError:
        return UploadValidationError(
            f"Submission exceeds the {self.settings.max_upload_files} "
            "document limit",
            code="TOO_MANY_FILES",
            status_code=413,
        )
