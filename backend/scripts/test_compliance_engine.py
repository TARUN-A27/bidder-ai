from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.core.config import get_settings
from app.schemas.compliance import (
    BidderClaims,
    BidderEvidenceBundle,
    BidderSubmissionManifest,
    RequirementEvaluationResult,
    TenderRequirementContext,
)
from app.schemas.normalized_documents import (
    AuditedFinancialsDocument,
    EmdEvidenceDocument,
    EpfoContributionStatusDocument,
    EpfoRegistrationDocument,
    EsicContributionStatusDocument,
    EsicRegistrationDocument,
    FinancialBoqDocument,
    GstRegistrationDocument,
    LocalContentDocument,
    NoBlacklistingDeclarationDocument,
    OemAuthorizationDocument,
    PanRecordDocument,
    ProductDatasheetDocument,
    SimilarExperienceDocument,
    TechnicalComplianceMatrixDocument,
    TurnoverCertificateDocument,
    UdyamRegistrationDocument,
    WarrantySlaUndertakingDocument,
)
from app.services.compliance.base import ComplianceEvaluationError
from app.services.compliance.compliance_engine import ComplianceEngine
from app.services.document_processing.azure_document_intelligence import (
    AzureDocumentIntelligenceService,
    DocumentExtractionError,
)
from app.services.document_processing.document_normalizer import DocumentNormalizer
from app.services.document_processing.normalizers.base import (
    DocumentNormalizationError,
)
from app.services.verification.mock_verification_loader import (
    MockVerificationError,
    MockVerificationLoader,
)


DATASET_ROOT = Path("/home/tarun/TARUN/projects/test-sih-docs")
CONFIG_PATH = DATASET_ROOT / "config" / "tender_requirements.json"
BIDDER_DIRECTORIES = (
    DATASET_ROOT / "bidders" / "Bidder_A_Low_Risk",
    DATASET_ROOT / "bidders" / "Bidder_B_High_Risk",
    DATASET_ROOT / "bidders" / "Bidder_C_Critical_Risk",
)

DOCUMENT_TYPES = {
    "02_GST_Registration_Certificate.pdf": "GST_REGISTRATION",
    "03_PAN_Record_Reference.pdf": "PAN_RECORD_REFERENCE",
    "04_Udyam_Registration_Certificate.pdf": "UDYAM_REGISTRATION",
    "05_EPFO_Registration_Letter.pdf": "EPFO_REGISTRATION",
    "06_EPFO_Contribution_Status_Aug_2026.pdf": "EPFO_CONTRIBUTION_STATUS",
    "07_ESIC_C11_Registration_Letter.pdf": "ESIC_REGISTRATION",
    "08_ESIC_Contribution_Status_Aug_2026.pdf": "ESIC_CONTRIBUTION_STATUS",
    "09_OEM_Authorization_Letter.pdf": "OEM_AUTHORIZATION",
    "10_Offered_Model_Product_Datasheet.pdf": "PRODUCT_DATASHEET",
    "12_CA_Average_Turnover_Certificate.pdf": "TURNOVER_CERTIFICATE",
    "13_Audited_Financial_Extracts_FY2022_25.pdf": "AUDITED_FINANCIALS",
    "14_Similar_Experience_Evidence_Bundle.pdf": "SIMILAR_EXPERIENCE",
    "15_Local_Content_Declaration_and_CA_Certificate.pdf": "LOCAL_CONTENT",
    "16_Technical_Compliance_Sheet.pdf": "TECHNICAL_COMPLIANCE_MATRIX",
    "17_Warranty_SLA_and_No_Cloud_Upload_Undertaking.pdf": (
        "WARRANTY_SLA_UNDERTAKING"
    ),
    "18_EMD_Exemption_Proof.pdf": "EMD_EVIDENCE",
    "18_EMD_Payment_Proof.pdf": "EMD_EVIDENCE",
    "19_Financial_Bid_BOQ.pdf": "FINANCIAL_BOQ",
    "20_No_Blacklisting_Self_Declaration.pdf": (
        "NO_BLACKLISTING_DECLARATION"
    ),
    "21_NSIC_SPR_Certificate.pdf": "EMD_EVIDENCE",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"Expected an object in {path}")
    return value


def build_manifest(raw: dict[str, Any]) -> BidderSubmissionManifest:
    return BidderSubmissionManifest(
        bidder_id=raw["bidder_id"],
        bidder_name=raw["bidder_name"],
        document_count=raw["document_count"],
        technical_packet_contains_bid_price_information=raw.get(
            "technical_packet_contains_bid_price_information"
        ),
        financial_price_file=raw.get("financial_price_file"),
        documents=raw.get("documents", []),
        quality_findings=raw.get("controlled_document_quality_findings") or [],
        material_contradictions=raw.get("controlled_material_contradictions")
        or [],
        deliberately_missing_documents=raw.get("deliberately_missing_documents")
        or [],
    )


def build_bidder_evidence(
    bidder_directory: Path,
    extraction_service: AzureDocumentIntelligenceService,
    normalizer: DocumentNormalizer,
) -> BidderEvidenceBundle:
    profile = load_json(bidder_directory / "bidder_profile.json")
    raw_manifest = load_json(bidder_directory / "document_manifest.json")
    manifest = build_manifest(raw_manifest)
    identity = profile["bidder_identity"]
    product = profile["offered_product"]
    values: dict[str, Any] = {
        "bidder_id": identity["bidder_id"],
        "legal_name": identity["legal_name"],
        "pan_reference": identity["pan"],
        "offered_model": product["model"],
        "claims": BidderClaims.model_validate(profile.get("claims", {})),
        "manifest": manifest,
        "emd_documents": [],
    }

    for document in manifest.documents:
        document_type = DOCUMENT_TYPES.get(document.file_name)
        if document_type is None:
            continue
        path = bidder_directory / "documents" / document.file_name
        if not path.is_file():
            raise AssertionError(f"Manifested document does not exist: {path}")
        print(
            f"Normalizing {manifest.bidder_id}: {document.file_name}",
            flush=True,
        )
        extraction = extraction_service.extract(path)
        normalized = normalizer.normalize(extraction, document_type=document_type)
        _store_normalized(values, normalized)

    return BidderEvidenceBundle.model_validate(values)


def _store_normalized(values: dict[str, Any], document: Any) -> None:
    mappings = (
        (GstRegistrationDocument, "gst"),
        (PanRecordDocument, "pan"),
        (UdyamRegistrationDocument, "udyam"),
        (EpfoRegistrationDocument, "epfo_registration"),
        (EpfoContributionStatusDocument, "epfo_contribution"),
        (EsicRegistrationDocument, "esic_registration"),
        (EsicContributionStatusDocument, "esic_contribution"),
        (TurnoverCertificateDocument, "turnover"),
        (AuditedFinancialsDocument, "audited_financials"),
        (SimilarExperienceDocument, "experience"),
        (OemAuthorizationDocument, "oem_authorization"),
        (ProductDatasheetDocument, "product_datasheet"),
        (LocalContentDocument, "local_content"),
        (TechnicalComplianceMatrixDocument, "technical_matrix"),
        (WarrantySlaUndertakingDocument, "warranty"),
        (FinancialBoqDocument, "financial_boq"),
        (NoBlacklistingDeclarationDocument, "no_blacklisting"),
    )
    if isinstance(document, EmdEvidenceDocument):
        values["emd_documents"].append(document)
        return
    for model_type, field_name in mappings:
        if isinstance(document, model_type):
            values[field_name] = document
            return
    raise AssertionError(f"Unhandled normalized model: {type(document).__name__}")


def validate_result_set(
    context: TenderRequirementContext,
    results: list[RequirementEvaluationResult],
) -> None:
    if len(results) != 16:
        raise AssertionError(f"Expected 16 results, received {len(results)}")
    codes = [result.requirement_code for result in results]
    if len(codes) != len(set(codes)):
        raise AssertionError("Duplicate compliance requirement results")
    if codes != context.requirement_codes:
        raise AssertionError("Result order/codes differ from tender configuration")
    invalid = [
        result
        for result in results
        if result.status not in context.allowed_statuses
    ]
    if invalid:
        raise AssertionError(f"Invalid compliance statuses: {invalid}")
    for result in results:
        if result.requires_human_review != (result.status == "NEEDS_REVIEW"):
            raise AssertionError(
                f"Human-review flag mismatch for {result.requirement_code}"
            )


def compare_with_expected_fixture(
    bidder_directory: Path,
    results: list[RequirementEvaluationResult],
) -> None:
    """Regression-only comparison after independent engine evaluation."""
    expected_payload = load_json(bidder_directory / "expected_result.json")
    expected = {
        item["requirement_id"]: item["expected_status"]
        for item in expected_payload["requirement_results"]
    }
    actual = {result.requirement_code: result.status for result in results}
    if actual != expected:
        differences = {
            code: {"actual": actual.get(code), "expected": expected.get(code)}
            for code in sorted(set(actual) | set(expected))
            if actual.get(code) != expected.get(code)
        }
        raise AssertionError(
            f"Fixture status mismatch for {bidder_directory.name}: {differences}"
        )


def print_results(label: str, results: list[RequirementEvaluationResult]) -> None:
    print(f"\n{label}")
    print(f"{'REQUIREMENT':<22} STATUS")
    for result in results:
        print(f"{result.requirement_code:<22} {result.status}")


def main() -> int:
    try:
        context = TenderRequirementContext.from_config(load_json(CONFIG_PATH))
        engine = ComplianceEngine()
        verification_loader = MockVerificationLoader()
        normalizer = DocumentNormalizer()
        settings = get_settings()

        with AzureDocumentIntelligenceService(settings) as extraction_service:
            for bidder_directory in BIDDER_DIRECTORIES:
                bidder = build_bidder_evidence(
                    bidder_directory, extraction_service, normalizer
                )
                verification = verification_loader.load(
                    bidder_directory / "mock_portal_data.json"
                )
                results = engine.evaluate(context, bidder, verification)
                validate_result_set(context, results)
                print_results(bidder_directory.name, results)
                compare_with_expected_fixture(bidder_directory, results)
    except (
        AssertionError,
        ComplianceEvaluationError,
        DocumentExtractionError,
        DocumentNormalizationError,
        MockVerificationError,
        OSError,
        ValueError,
    ) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nPASS: all compliance engine assertions and fixture comparisons passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
