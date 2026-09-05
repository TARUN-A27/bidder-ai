from __future__ import annotations


class IngestionError(Exception):
    """Base class for controlled bidder-package ingestion errors."""


class InvalidSubmissionArchiveError(IngestionError):
    pass


class UnsafeArchivePathError(IngestionError):
    pass


class UnsupportedFileTypeError(IngestionError):
    pass


class InvalidPdfError(IngestionError):
    pass


class DuplicateSubmissionError(IngestionError):
    pass


class ManifestValidationError(IngestionError):
    pass


class SubmissionStorageError(IngestionError):
    pass


class IngestionMetadataError(IngestionError):
    pass


class TenderNotFoundError(IngestionError):
    pass


class BidderIdentityConflictError(IngestionError):
    pass
