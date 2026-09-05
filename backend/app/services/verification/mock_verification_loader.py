from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from app.schemas.verification_evidence import (
    DebarmentRegistryEvidence,
    DpiitRegistryEvidence,
    EmdVerificationEvidence,
    EpfoRegistryEvidence,
    EsicRegistryEvidence,
    GstRegistryEvidence,
    GstReturnEvidence,
    IssuerVerificationEvidence,
    IssuerVerifiedExperienceRecord,
    LocalContentVerificationEvidence,
    NsicRegistryEvidence,
    OemAuthorizationRegistryEvidence,
    PanRegistryEvidence,
    ProductCertificationRegistryEvidence,
    ProductDatasheetRegistryEvidence,
    UdyamRegistryEvidence,
    VerificationEvidenceBundle,
)


class MockVerificationError(Exception):
    """Base exception for mock verification loading failures."""


class MockVerificationFileNotFoundError(MockVerificationError):
    """Raised when the requested mock verification file is absent."""


class MockVerificationValidationError(MockVerificationError):
    """Raised when mock verification JSON is malformed or invalid."""


PROHIBITED_DECISION_STATES = {
    "COMPLIANT",
    "NON_COMPLIANT",
    "MISSING",
    "NEEDS_REVIEW",
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


def _canonical_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).split()).strip()
    return normalized.upper() or None


def _factual_state(value: Any) -> str | None:
    normalized = _canonical_text(value)
    if normalized in PROHIBITED_DECISION_STATES:
        return None
    return normalized


class MockVerificationLoader:
    """Load typed authoritative evidence from a mock portal JSON snapshot."""

    _known_handlers: dict[
        str,
        tuple[str, Callable[[dict[str, Any], dict[str, Any]], Any]],
    ]

    def __init__(self) -> None:
        self._known_handlers = {
            "gst": ("gst", self._load_gst),
            "pan": ("pan", self._load_pan),
            "udyam": ("udyam", self._load_udyam),
            "epfo": ("epfo", self._load_epfo),
            "esic": ("esic", self._load_esic),
            "dpiit": ("dpiit", self._load_dpiit),
            "nsic": ("nsic", self._load_nsic),
            "debarment": ("debarment", self._load_debarment),
            "oem_authorization": (
                "oem_authorization",
                self._load_oem_authorization,
            ),
            "product_certification": (
                "product_certification",
                self._load_product_certification,
            ),
            "product_datasheet": (
                "product_datasheet",
                self._load_product_datasheet,
            ),
            "local_content": ("local_content", self._load_local_content),
            "experience_verification": (
                "issuer_verification",
                self._load_issuer_verification,
            ),
            "emd_exemption": ("emd", self._load_emd_exemption),
            "emd_payment": ("emd", self._load_emd_payment),
        }

    def load(self, source_path: str | Path) -> VerificationEvidenceBundle:
        path = Path(source_path).expanduser()
        if not path.exists():
            raise MockVerificationFileNotFoundError(
                f"Mock verification file does not exist: {path}"
            )
        if not path.is_file():
            raise MockVerificationValidationError(
                f"Mock verification path is not a file: {path}"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MockVerificationValidationError(
                f"Malformed mock verification JSON in {path.name}: "
                f"line {exc.lineno}, column {exc.colno}"
            ) from exc
        except OSError as exc:
            raise MockVerificationValidationError(
                f"Could not read mock verification file: {path}"
            ) from exc

        if not isinstance(payload, dict):
            raise MockVerificationValidationError(
                f"Mock verification root must be an object: {path.name}"
            )
        records = payload.get("records")
        if not isinstance(records, dict):
            raise MockVerificationValidationError(
                f"Mock verification records must be an object: {path.name}"
            )

        bundle_values: dict[str, Any] = {
            "dataset_id": payload.get("dataset_id"),
            "bidder_id": payload.get("bidder_id"),
            "canonical_identity_reference": payload.get(
                "canonical_identity_reference"
            ),
            "snapshot_at": payload.get("snapshot_at"),
            "data_classification": payload.get("data_classification"),
            "disclaimer": payload.get("disclaimer"),
            "synthetic": payload.get("synthetic", True),
        }
        unknown_sources: dict[str, Any] = {}

        try:
            for source_key, record in records.items():
                handler_entry = self._known_handlers.get(source_key)
                if handler_entry is None:
                    unknown_sources[source_key] = record
                    continue
                if not isinstance(record, dict):
                    raise ValueError(f"record {source_key!r} must be an object")
                response = record.get("response")
                if not isinstance(response, dict):
                    raise ValueError(
                        f"record {source_key!r}.response must be an object"
                    )
                bundle_field, handler = handler_entry
                bundle_values[bundle_field] = handler(record, response)

            bundle_values["unknown_sources"] = unknown_sources
            return VerificationEvidenceBundle.model_validate(bundle_values)
        except (ValidationError, ValueError, TypeError) as exc:
            raise MockVerificationValidationError(
                f"Invalid mock verification data in {path.name}: {exc}"
            ) from exc

    @staticmethod
    def _metadata(record: dict[str, Any], source_key: str) -> dict[str, Any]:
        source_system = record.get("source_system")
        if not isinstance(source_system, str) or not source_system.strip():
            raise ValueError(f"record {source_key!r} has no source_system")
        return {
            "source_key": source_key,
            "source_system": source_system,
            "source_snapshot_at": record.get("snapshot_at"),
            "verification_status": _factual_state(
                record.get("verification_status")
            ),
            "record_classification": record.get("record_classification"),
            "synthetic": record.get("synthetic"),
        }

    def _load_gst(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> GstRegistryEvidence:
        returns = [
            GstReturnEvidence(
                period=item.get("period"),
                gstr1_status=_factual_state(item.get("gstr1_status")),
                gstr1_filed_on=item.get("gstr1_filed_on"),
                gstr3b_status=_factual_state(item.get("gstr3b_status")),
                gstr3b_filed_on=item.get("gstr3b_filed_on"),
            )
            for item in response.get("returns", [])
            if isinstance(item, dict)
        ]
        periods = [item.period for item in returns]
        latest_period = response.get("compliant_through")
        if not latest_period and periods:
            latest_period = max(periods)
        return GstRegistryEvidence(
            **self._metadata(record, "gst"),
            gstin=response.get("gstin"),
            legal_name=response.get("legal_name"),
            pan_reference=response.get("pan"),
            status=_factual_state(response.get("status")),
            effective_date=response.get("registration_date"),
            cancellation_date=response.get("cancellation_date"),
            status_at_bid_close=_factual_state(
                response.get("status_at_bid_close")
            ),
            latest_return_period=latest_period,
            missing_return_periods=response.get(
                "unfiled_periods_due_through_august_2026", []
            ),
            returns=returns,
        )

    def _load_pan(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> PanRegistryEvidence:
        return PanRegistryEvidence(
            **self._metadata(record, "pan"),
            pan_reference=response.get("authoritative_pan", response.get("pan")),
            legal_name=response.get(
                "authoritative_legal_name", response.get("legal_name")
            ),
            entity_type=response.get(
                "authoritative_entity_type", response.get("entity_type")
            ),
            status=_factual_state(response.get("status")),
            incorporation_date=response.get("incorporation_date"),
            identity_match=_factual_state(response.get("identity_match")),
            uploaded_pan_reference=response.get("uploaded_pan"),
            uploaded_legal_name=response.get("uploaded_legal_name"),
        )

    def _load_udyam(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> UdyamRegistryEvidence:
        return UdyamRegistryEvidence(
            **self._metadata(record, "udyam"),
            udyam_number=response.get("registration_number"),
            enterprise_name=response.get("enterprise_name"),
            pan_reference=response.get("pan"),
            classification=response.get("classification"),
            status=_factual_state(response.get("status")),
            relevant_activity=response.get("relevant_activity"),
            activities=response.get("activities", []),
        )

    def _load_epfo(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> EpfoRegistryEvidence:
        payment_status = next(
            (
                value
                for key, value in response.items()
                if key.endswith("_payment_status")
            ),
            None,
        )
        return EpfoRegistryEvidence(
            **self._metadata(record, "epfo"),
            establishment_code=response.get("establishment_code"),
            establishment_name=response.get("establishment_name"),
            pan_reference=response.get("pan"),
            registration_status=_factual_state(
                response.get("registration_status")
            ),
            contribution_state=_factual_state(
                response.get("contribution_status")
            ),
            compliant_through=response.get("compliant_through"),
            latest_due_period=response.get("latest_due_period"),
            latest_period=(
                response.get("latest_due_period")
                or response.get("compliant_through")
            ),
            payment_status=_factual_state(payment_status),
            payment_date=response.get("latest_payment_date"),
            due_date=response.get("synthetic_due_date"),
            outstanding_amount=response.get("outstanding_amount_inr"),
            portal_document_match=response.get("portal_document_match"),
        )

    def _load_esic(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> EsicRegistryEvidence:
        return EsicRegistryEvidence(
            **self._metadata(record, "esic"),
            employer_code=response.get("employer_code"),
            employer_name=response.get("employer_name"),
            pan_reference=response.get("pan"),
            registration_status=_factual_state(
                response.get("registration_status")
            ),
            status_at_bid_close=_factual_state(
                response.get("status_at_bid_close")
            ),
            contribution_state=_factual_state(
                response.get("contribution_status")
            ),
            compliant_through=response.get("compliant_through"),
            latest_period=response.get("compliant_through"),
            payment_date=response.get("latest_payment_date"),
            outstanding_amount=response.get("outstanding_amount_inr"),
            default_reason=response.get("default_reason"),
        )

    def _load_dpiit(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> DpiitRegistryEvidence:
        return DpiitRegistryEvidence(
            **self._metadata(record, "dpiit"),
            claim_submitted=response.get("claim_submitted"),
            applicability=response.get("applicability"),
            reason=response.get("reason"),
            recognition_number=response.get("recognition_reference"),
            entity_name=response.get("recognized_entity"),
            pan_reference=response.get("pan"),
            entity_type=response.get("entity_type"),
            recognition_date=response.get("recognition_date"),
            valid_through=response.get("valid_through"),
            status=_factual_state(response.get("status")),
            identity_match=_factual_state(response.get("identity_match")),
            claim_submitted_on=response.get("claim_submitted_on"),
            claim_before_bid_deadline=response.get("claim_before_bid_deadline"),
            tender_permits_relaxation=response.get(
                "tender_explicitly_permits_relaxation"
            ),
            relaxed_requirement_ids=response.get("relaxed_requirement_ids", []),
            automatic_exemption_assumed=response.get(
                "automatic_exemption_assumed"
            ),
        )

    def _load_nsic(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> NsicRegistryEvidence:
        return NsicRegistryEvidence(
            **self._metadata(record, "nsic"),
            claim_submitted=response.get("claim_submitted"),
            applicability=response.get("applicability"),
            reason=response.get("reason"),
            registration_number=response.get("spr_number"),
            entity_name=response.get("enterprise_name"),
            pan_reference=response.get("pan"),
            status=_factual_state(response.get("status")),
            valid_from=response.get("valid_from"),
            valid_through=response.get("valid_through"),
            covered_categories=response.get("covered_categories", []),
            tender_category_relevant=response.get("tender_category_relevant"),
            automatic_benefit_assumed=response.get(
                "automatic_benefit_assumed"
            ),
        )

    def _load_debarment(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> DebarmentRegistryEvidence:
        return DebarmentRegistryEvidence(
            **self._metadata(record, "debarment"),
            entity_name=response.get("entity_name"),
            pan_reference=response.get("pan"),
            active=response.get("active_debarment"),
            status=_factual_state(response.get("status")),
            effective_from=response.get("effective_from"),
            valid_through=response.get("valid_through"),
            order_reference=response.get("order_reference"),
            searched_through=response.get("searched_through"),
            uploaded_self_declaration=response.get(
                "uploaded_self_declaration"
            ),
        )

    def _load_oem_authorization(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> OemAuthorizationRegistryEvidence:
        return OemAuthorizationRegistryEvidence(
            **self._metadata(record, "oem_authorization"),
            authorization_number=response.get("authorization_number"),
            oem_name=response.get("oem_legal_name"),
            oem_registry_id=response.get("oem_registry_id"),
            authorized_bidder=response.get("authorized_bidder"),
            bidder_pan=response.get("bidder_pan"),
            bid_number=response.get("bid_number"),
            brand=response.get("brand"),
            offered_model=response.get("model"),
            status=_factual_state(response.get("status")),
            document_present=response.get("document_present"),
            issue_date=response.get("issued_on"),
            valid_through=response.get("valid_through"),
            tender_required_through=response.get("tender_required_through"),
            status_at_bid_close=_factual_state(
                response.get("status_at_bid_close")
            ),
            validity_shortfall_days=response.get("validity_shortfall_days"),
        )

    def _load_product_certification(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> ProductCertificationRegistryEvidence:
        return ProductCertificationRegistryEvidence(
            **self._metadata(record, "product_certification"),
            certificate_type=response.get("certificate_type"),
            certificate_number=response.get("certificate_number"),
            certificate_standard=response.get("standard"),
            status=_factual_state(response.get("status")),
            certificate_holder=response.get("certificate_holder"),
            manufacturer=response.get("manufacturer"),
            covered_models=response.get("covered_models", []),
            report_number=response.get("test_report_number"),
            valid_from=response.get("valid_from"),
            valid_through=response.get("valid_through"),
            exact_model_match=response.get("exact_model_match"),
            certificate_report_match=response.get(
                "certificate_test_report_match"
            ),
        )

    def _load_product_datasheet(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> ProductDatasheetRegistryEvidence:
        return ProductDatasheetRegistryEvidence(
            **self._metadata(record, "product_datasheet"),
            oem_name=response.get("oem_legal_name"),
            oem_registry_id=response.get("oem_registry_id"),
            brand=response.get("brand"),
            model=response.get("model"),
            product_family=response.get("product_family"),
            sku=response.get("sku"),
            lifecycle_status=_factual_state(response.get("lifecycle_status")),
            technical_specifications=response.get(
                "technical_specifications", {}
            ),
            failed_technical_requirements=response.get(
                "failed_technical_requirements", []
            ),
        )

    def _load_local_content(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> LocalContentVerificationEvidence:
        return LocalContentVerificationEvidence(
            **self._metadata(record, "local_content"),
            entity_name=response.get("bidder"),
            oem_name=response.get("oem"),
            brand=response.get("brand"),
            offered_model=response.get("model"),
            declared_local_content_percentage=response.get("declared_percent"),
            verified_local_content_percentage=response.get("verified_percent"),
        )

    def _load_issuer_verification(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> IssuerVerificationEvidence:
        records = [
            IssuerVerifiedExperienceRecord(
                work_order_number=item.get("order"),
                issuer=item.get("customer"),
                scope=item.get("scope"),
                value=item.get("value_inr"),
                start_date=item.get("start"),
                completion_date=item.get("completion"),
                completion_status=_factual_state(item.get("status")),
                verification_reference=item.get("verification_reference"),
            )
            for item in response.get("completed_orders", [])
            if isinstance(item, dict)
        ]
        return IssuerVerificationEvidence(
            **self._metadata(record, "experience_verification"),
            entity_name=response.get("bidder"),
            experience_years=response.get("experience_years"),
            records=records,
        )

    def _load_emd_exemption(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> EmdVerificationEvidence:
        return EmdVerificationEvidence(
            **self._metadata(record, "emd_exemption"),
            evidence_type="EXEMPTION",
            entity_name=response.get("bidder"),
            bid_number=response.get("bid_number"),
            exemption_claimed=True,
            claim_submitted_on=response.get("claim_submitted_on"),
            tender_permits_exemption=response.get("tender_permits_exemption"),
            bidder_identity_match=response.get("identity_match"),
            udyam_valid=response.get("udyam_valid"),
            nsic_valid=response.get("nsic_valid"),
            nsic_category_relevant=response.get("nsic_category_relevant"),
            automatic_benefit_assumed=response.get(
                "automatic_benefit_assumed"
            ),
            final_acceptance_authority=response.get(
                "final_acceptance_authority"
            ),
        )

    def _load_emd_payment(
        self,
        record: dict[str, Any],
        response: dict[str, Any],
    ) -> EmdVerificationEvidence:
        return EmdVerificationEvidence(
            **self._metadata(record, "emd_payment"),
            evidence_type="PAYMENT",
            entity_name=response.get("bidder"),
            pan_reference=response.get("bidder_pan"),
            bid_number=response.get("bid_number"),
            amount=response.get("emd_amount_inr"),
            payment_reference=response.get("payment_reference"),
            payment_status=_factual_state(response.get("payment_status")),
            payment_date=response.get("payment_date"),
            bid_deadline=response.get("bid_deadline"),
            paid_before_bid_deadline=response.get("paid_before_bid_deadline"),
            payment_reference_valid=response.get("payment_reference_valid"),
            bid_number_match=response.get("bid_number_match"),
            bidder_identity_match=response.get("bidder_identity_match"),
            exemption_claimed=response.get("emd_exemption_claimed"),
        )
