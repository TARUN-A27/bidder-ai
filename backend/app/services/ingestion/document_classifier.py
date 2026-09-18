from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentClassification:
    document_code: str | None
    document_type: str


_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), code, document_type)
    for pattern, code, document_type in (
        (r"bid[_ -]*cover.*tender[_ -]*acceptance", "DOC-01", "BID_COVER"),
        (r"gst[_ -]*registration", "DOC-02", "GST_REGISTRATION"),
        (r"pan[_ -]*(record|reference)", "DOC-03", "PAN_RECORD_REFERENCE"),
        (r"udyam[_ -]*registration", "DOC-04", "UDYAM_REGISTRATION"),
        (r"epfo[_ -]*registration", "DOC-05", "EPFO_REGISTRATION"),
        (r"epfo[_ -]*contribution", "DOC-06", "EPFO_CONTRIBUTION_STATUS"),
        (r"esic[_ -].*registration", "DOC-07", "ESIC_REGISTRATION"),
        (r"esic[_ -]*contribution", "DOC-08", "ESIC_CONTRIBUTION_STATUS"),
        (r"dpiit[_ -]*(recognition|certificate)", "DOC-09", "DPIIT_RECOGNITION"),
        (r"nsic[_ -]*(spr|registration|certificate)", "DOC-10", "NSIC_REGISTRATION"),
        (r"oem[_ -]*authorization", "DOC-11", "OEM_AUTHORIZATION"),
        (r"(product[_ -]*datasheet|offered[_ -]*model.*datasheet)", "DOC-12", "PRODUCT_DATASHEET"),
        (r"iec[_ -]*62368.*(certificate|report)", "DOC-13", "PRODUCT_CERTIFICATION"),
        (r"(average[_ -]*turnover|turnover[_ -]*certificate)", "DOC-14", "TURNOVER_CERTIFICATE"),
        (r"audited[_ -]*(financial|extract)", "DOC-15", "AUDITED_FINANCIALS"),
        (r"similar[_ -]*experience", "DOC-16", "SIMILAR_EXPERIENCE"),
        (r"local[_ -]*content", "DOC-17", "LOCAL_CONTENT"),
        (r"technical[_ -]*compliance", "DOC-18", "TECHNICAL_COMPLIANCE_MATRIX"),
        (r"warranty[_ -]*sla", "DOC-19", "WARRANTY_SLA_UNDERTAKING"),
        (r"emd[_ -]*(payment|exemption|proof)", "DOC-20", "EMD_EVIDENCE"),
        (r"(financial[_ -]*(bid|boq)|bid[_ -]*boq)", "DOC-21", "FINANCIAL_BOQ"),
        (r"(no[_ -]*blacklisting|debarment[_ -]*declaration)", "DOC-22", "NO_BLACKLISTING_DECLARATION"),
    )
)


def classify_document(filename: str) -> DocumentClassification:
    for pattern, code, document_type in _RULES:
        if pattern.search(filename):
            return DocumentClassification(code, document_type)
    return DocumentClassification(None, "UNKNOWN")


def classify_document_content(content: str) -> DocumentClassification:
    """Conservative content-based fallback for officer-supplied generic filenames."""

    text = re.sub(r"\s+", " ", content or "").upper()
    checks: tuple[tuple[tuple[str, ...], str, str], ...] = (
        (("GSTIN", "LEGAL NAME"), "DOC-02", "GST_REGISTRATION"),
        (("PERMANENT ACCOUNT NUMBER",), "DOC-03", "PAN_RECORD_REFERENCE"),
        (("PAN REFERENCE", "LEGAL NAME"), "DOC-03", "PAN_RECORD_REFERENCE"),
        (("UDYAM", "ENTERPRISE NAME"), "DOC-04", "UDYAM_REGISTRATION"),
        (("EPFO", "ESTABLISHMENT"), "DOC-05", "EPFO_REGISTRATION"),
        (("EPFO", "CONTRIBUTION"), "DOC-06", "EPFO_CONTRIBUTION_STATUS"),
        (("ESIC", "EMPLOYER CODE"), "DOC-07", "ESIC_REGISTRATION"),
        (("ESIC", "CONTRIBUTION"), "DOC-08", "ESIC_CONTRIBUTION_STATUS"),
        (("DPIIT", "RECOGNITION"), "DOC-09", "DPIIT_RECOGNITION"),
        (("NSIC", "SINGLE POINT REGISTRATION"), "DOC-10", "NSIC_REGISTRATION"),
        (("OEM", "AUTHORIZATION"), "DOC-11", "OEM_AUTHORIZATION"),
        (("MODEL", "SCANNING SPEED"), "DOC-12", "PRODUCT_DATASHEET"),
        (("IEC 62368",), "DOC-13", "PRODUCT_CERTIFICATION"),
        (("AVERAGE TURNOVER",), "DOC-14", "TURNOVER_CERTIFICATE"),
        (("AUDITED", "FINANCIAL"), "DOC-15", "AUDITED_FINANCIALS"),
        (("SIMILAR EXPERIENCE",), "DOC-16", "SIMILAR_EXPERIENCE"),
        (("LOCAL CONTENT",), "DOC-17", "LOCAL_CONTENT"),
        (("TECHNICAL COMPLIANCE",), "DOC-18", "TECHNICAL_COMPLIANCE_MATRIX"),
        (("WARRANTY", "SLA"), "DOC-19", "WARRANTY_SLA_UNDERTAKING"),
        (("EMD", "PAYMENT"), "DOC-20", "EMD_EVIDENCE"),
        (("EMD", "EXEMPTION"), "DOC-20", "EMD_EVIDENCE"),
        (("FINANCIAL BID", "BOQ"), "DOC-21", "FINANCIAL_BOQ"),
        (("BLACKLIST", "DECLARATION"), "DOC-22", "NO_BLACKLISTING_DECLARATION"),
    )
    for required_tokens, code, document_type in checks:
        if all(token in text for token in required_tokens):
            return DocumentClassification(code, document_type)
    return DocumentClassification(None, "UNKNOWN")
