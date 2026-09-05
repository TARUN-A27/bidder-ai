from __future__ import annotations


class BidGuardError(Exception):
    """Base class for controlled application errors."""


class DatabaseUnavailableError(BidGuardError):
    pass


class SubmissionNotFoundError(BidGuardError):
    pass


class SubmissionAlreadyHasDocumentsError(BidGuardError):
    pass


class SubmissionStorageConflictError(BidGuardError):
    pass


class UploadValidationError(BidGuardError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "INVALID_UPLOAD",
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
