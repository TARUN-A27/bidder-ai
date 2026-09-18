from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace

import pytest

from app.core.logging import COMPONENT_LOGS, configure_logging
from app.services.assessment.assessment_service import AssessmentService
from app.services.document_processing.azure_document_intelligence import (
    AzureDocumentIntelligenceService,
)


def flush_logs() -> None:
    for logger_name in ("", *COMPONENT_LOGS):
        for handler in logging.getLogger(logger_name).handlers:
            handler.flush()


def test_logging_configuration_creates_rotating_component_files(
    settings_factory, tmp_path
):
    settings = settings_factory(
        "storage",
        log_root=tmp_path / "workflow-logs",
        log_max_bytes=5 * 1024 * 1024,
        log_backup_count=3,
    )

    log_root = configure_logging(settings)
    logging.getLogger("bidguard.assessment").info("ASSESSMENT TEST EVENT")
    logging.getLogger("bidguard.ingestion").info("INGESTION TEST EVENT")
    logging.getLogger("bidguard.azure").info("AZURE TEST EVENT")
    logging.getLogger("bidguard.database").info("DATABASE TEST EVENT")
    logging.getLogger("bidguard.runtime").error("RUNTIME TEST ERROR")
    flush_logs()

    expected = {"bidguard.log", "errors.log", *COMPONENT_LOGS.values()}
    assert {path.name for path in log_root.iterdir()} == expected
    assert "ASSESSMENT TEST EVENT" in (log_root / "assessment.log").read_text()
    assert "INGESTION TEST EVENT" in (log_root / "ingestion.log").read_text()
    assert "AZURE TEST EVENT" in (log_root / "azure.log").read_text()
    assert "DATABASE TEST EVENT" in (log_root / "database.log").read_text()
    assert "RUNTIME TEST ERROR" in (log_root / "errors.log").read_text()
    assert "ASSESSMENT TEST EVENT" in (log_root / "bidguard.log").read_text()
    handlers = [
        handler for handler in logging.getLogger("bidguard.assessment").handlers
        if isinstance(handler, RotatingFileHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].maxBytes == 5 * 1024 * 1024
    assert handlers[0].backupCount == 3


def test_logging_redacts_configured_and_pattern_secrets(settings_factory, tmp_path):
    settings = settings_factory(
        "storage-redaction",
        log_root=tmp_path / "logs",
        oracle_password="oracle-secret-value",
        azure_document_intelligence_key="azure-secret-value",
    )
    configure_logging(settings)

    logging.getLogger("bidguard.database").error(
        "SECURITY TEST | password=plain-secret token=token-secret configured=%s/%s",
        settings.oracle_password,
        settings.azure_document_intelligence_key.get_secret_value(),
    )
    flush_logs()
    content = (settings.log_root / "errors.log").read_text()

    assert "plain-secret" not in content
    assert "token-secret" not in content
    assert "oracle-secret-value" not in content
    assert "azure-secret-value" not in content
    assert "[REDACTED]" in content


def test_assessment_start_and_failure_events_do_not_log_exception_text(
    settings_factory, tmp_path
):
    settings = settings_factory("storage-assessment", log_root=tmp_path / "logs")
    configure_logging(settings)

    repository = SimpleNamespace(
        submission=lambda _submission_id: (_ for _ in ()).throw(
            RuntimeError("raw OCR text must remain private")
        )
    )
    service = AssessmentService(repository, SimpleNamespace())
    with pytest.raises(RuntimeError, match="raw OCR text"):
        service.run_assessment("submission-1")
    flush_logs()
    content = (settings.log_root / "assessment.log").read_text()

    assert "ASSESSMENT START" in content
    assert "ASSESSMENT FAILED" in content
    assert "submission_id=submission-1" in content
    assert "error_type=RuntimeError" in content
    assert "raw OCR text must remain private" not in content


def test_azure_events_never_log_extracted_text(settings_factory, tmp_path):
    settings = settings_factory("storage-azure", log_root=tmp_path / "logs")
    configure_logging(settings)
    pdf_path = tmp_path / "evidence.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 synthetic test")
    raw_text = "RAW_OCR_CONTENT_MUST_NOT_BE_LOGGED"
    result = SimpleNamespace(
        pages=[SimpleNamespace(
            page_number=1,
            lines=[SimpleNamespace(content=raw_text)],
        )],
        tables=[],
        content=raw_text,
    )

    class Poller:
        def result(self):
            return result

    service = AzureDocumentIntelligenceService.__new__(
        AzureDocumentIntelligenceService
    )
    service.model_id = "prebuilt-layout"
    service._client = SimpleNamespace(
        begin_analyze_document=lambda *_args, **_kwargs: Poller()
    )

    extraction = service.extract(pdf_path)
    flush_logs()
    content = (settings.log_root / "azure.log").read_text()

    assert extraction.content == raw_text
    assert "AZURE_DI START" in content
    assert "AZURE_DI COMPLETE" in content
    assert "document=evidence.pdf" in content
    assert raw_text not in content
