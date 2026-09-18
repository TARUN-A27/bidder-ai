from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import Settings


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
COMPONENT_LOGS = {
    "bidguard.assessment": "assessment.log",
    "bidguard.ingestion": "ingestion.log",
    "bidguard.azure": "azure.log",
    "bidguard.database": "database.log",
}
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization)"
    r"\s*[:=]\s*([^\s|,;]+)"
)
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[^\s|,;]+")


class RedactingFormatter(logging.Formatter):
    def __init__(self, fmt: str, secrets: tuple[str, ...] = ()) -> None:
        super().__init__(fmt)
        self.secrets = tuple(secret for secret in secrets if secret)

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        for secret in self.secrets:
            rendered = rendered.replace(secret, "[REDACTED]")
        rendered = _SENSITIVE_ASSIGNMENT.sub(r"\1=[REDACTED]", rendered)
        return _BEARER_TOKEN.sub("Bearer [REDACTED]", rendered)


def _owned(handler: logging.Handler) -> bool:
    return bool(getattr(handler, "_bidguard_handler", False))


def _mark(handler: logging.Handler) -> logging.Handler:
    handler._bidguard_handler = True  # type: ignore[attr-defined]
    return handler


def _file_handler(
    path: Path,
    formatter: logging.Formatter,
    settings: Settings,
    level: int = logging.INFO,
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return _mark(handler)  # type: ignore[return-value]


def configure_logging(settings: Settings) -> Path:
    """Configure console and rotating workflow logs without duplicate handlers."""
    log_root = settings.log_root.resolve()
    log_root.mkdir(parents=True, exist_ok=True)
    secrets = (
        settings.azure_document_intelligence_key.get_secret_value(),
        settings.oracle_password,
    )
    formatter = RedactingFormatter(LOG_FORMAT, secrets)

    root = logging.getLogger()
    for handler in list(root.handlers):
        if _owned(handler):
            root.removeHandler(handler)
            handler.close()
    root.setLevel(logging.INFO)

    console = _mark(logging.StreamHandler())
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(_file_handler(log_root / "bidguard.log", formatter, settings))
    root.addHandler(
        _file_handler(log_root / "errors.log", formatter, settings, logging.ERROR)
    )

    for logger_name, file_name in COMPONENT_LOGS.items():
        component = logging.getLogger(logger_name)
        for handler in list(component.handlers):
            if _owned(handler):
                component.removeHandler(handler)
                handler.close()
        component.setLevel(logging.INFO)
        component.propagate = True
        component.addHandler(_file_handler(log_root / file_name, formatter, settings))

    return log_root
