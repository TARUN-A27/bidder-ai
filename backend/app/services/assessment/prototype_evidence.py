from __future__ import annotations

import json
from pathlib import Path

from app.schemas.compliance import BidderEvidenceBundle, BidderSubmissionManifest, TenderRequirementContext
from app.services.assessment.errors import AssessmentInputError
from app.services.document_processing.azure_document_intelligence import AzureDocumentIntelligenceService, AzureConfigurationError
from app.services.document_processing.document_normalizer import DocumentNormalizer
from app.services.document_processing.normalizers.base import DocumentNormalizationError
from app.services.scoring.config_loader import ScoringConfigLoader, ScoringConfigurationError
from app.services.verification.mock_verification_loader import MockVerificationLoader, MockVerificationError


DOCUMENT_FIELDS = {
    "GST_REGISTRATION": "gst", "PAN_RECORD_REFERENCE": "pan", "UDYAM_REGISTRATION": "udyam",
    "EPFO_REGISTRATION": "epfo_registration", "EPFO_CONTRIBUTION_STATUS": "epfo_contribution",
    "ESIC_REGISTRATION": "esic_registration", "ESIC_CONTRIBUTION_STATUS": "esic_contribution",
    "TURNOVER_CERTIFICATE": "turnover", "AUDITED_FINANCIALS": "audited_financials",
    "SIMILAR_EXPERIENCE": "experience", "OEM_AUTHORIZATION": "oem_authorization",
    "PRODUCT_DATASHEET": "product_datasheet", "LOCAL_CONTENT": "local_content",
    "TECHNICAL_COMPLIANCE_MATRIX": "technical_matrix", "WARRANTY_SLA_UNDERTAKING": "warranty",
    "FINANCIAL_BOQ": "financial_boq", "NO_BLACKLISTING_DECLARATION": "no_blacklisting",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PrototypeEvidenceProvider:
    """Resolve the configured prototype dataset using DB identity, never URL paths."""

    def __init__(self, settings):
        self.settings = settings
        self.root = settings.prototype_dataset_root

    def resolve(self, submission):
        matches = []
        for path in sorted((self.root / "bidders").glob("*/bidder_profile.json")):
            profile = read_json(path)
            identity = profile["bidder_identity"]
            if (profile["dataset_id"] == submission.dataset_id
                    and identity["pan"] == submission.pan_reference
                    and identity["legal_name"] == submission.bidder_name):
                matches.append((path.parent, profile))
        if len(matches) != 1:
            raise AssessmentInputError("No unique prototype evidence matches this submission")
        return matches[0]

    def load(self, submission):
        try:
            directory, profile = self.resolve(submission)
            config = read_json(self.root / "config/tender_requirements.json")
            context = TenderRequirementContext.from_config(config)
            rules = ScoringConfigLoader().load(self.root / "config/scoring_rules.json")
            if (context.dataset_id != submission.dataset_id or context.bid_number != submission.bid_number
                    or rules.dataset_id != context.dataset_id):
                raise AssessmentInputError("Submission and prototype tender configuration differ")
            if submission.offered_model != profile["offered_product"]["model"]:
                raise AssessmentInputError("Submission offered model differs from prototype evidence")
            raw = read_json(directory / "document_manifest.json")
            manifest = BidderSubmissionManifest(
                **{key: raw[key] for key in ("bidder_id", "bidder_name", "document_count", "documents")},
                technical_packet_contains_bid_price_information=raw.get("technical_packet_contains_bid_price_information"),
                financial_price_file=raw.get("financial_price_file"),
                quality_findings=raw.get("controlled_document_quality_findings", []),
                deliberately_missing_documents=raw.get("deliberately_missing_documents", []))
            values = dict(bidder_id=profile["bidder_identity"]["bidder_id"], legal_name=submission.bidder_name,
                          pan_reference=submission.pan_reference, offered_model=submission.offered_model,
                          manifest=manifest, claims=dict(mse_purchase_preference=submission.mse_claimed,
                          startup_turnover_relaxation=submission.startup_claimed,
                          nsic_related_benefit=submission.nsic_claimed, emd_exemption=submission.emd_exemption_claimed,
                          mii_purchase_preference=profile["claims"].get("mii_purchase_preference", False)), emd_documents=[])
            normalizer = DocumentNormalizer()
            with AzureDocumentIntelligenceService(self.settings) as extractor:
                for item in manifest.documents:
                    path = (directory / "documents" / item.file_name).resolve()
                    if path.parent != (directory / "documents").resolve() or not path.is_file():
                        raise AssessmentInputError("A manifested prototype document is unavailable")
                    # Phase 1 has no normalizer for these supporting documents.
                    if item.file_name.startswith(("01_", "11_")) or "DPIIT_Recognition" in item.file_name:
                        continue
                    extraction = extractor.extract(path)
                    explicit = "EMD_EVIDENCE" if "EMD_Payment" in item.file_name else None
                    document = normalizer.normalize(extraction, document_type=explicit)
                    if document.document_type == "EMD_EVIDENCE":
                        values["emd_documents"].append(document)
                    else:
                        values[DOCUMENT_FIELDS[document.document_type]] = document
            bidder = BidderEvidenceBundle.model_validate(values)
            verification = MockVerificationLoader().load(directory / "mock_portal_data.json")
            return context, bidder, verification, rules
        except AssessmentInputError:
            raise
        except (OSError, ValueError, KeyError, DocumentNormalizationError, AzureConfigurationError,
                MockVerificationError, ScoringConfigurationError) as exc:
            raise AssessmentInputError("Required prototype evidence or configuration is unavailable or invalid") from exc
