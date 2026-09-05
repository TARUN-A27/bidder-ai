from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.schemas.verification_evidence import VerificationEvidenceBundle
from app.services.verification.mock_verification_loader import (
    MockVerificationFileNotFoundError,
    MockVerificationLoader,
    MockVerificationValidationError,
)


DATASET_ROOT = Path("/home/tarun/TARUN/projects/test-sih-docs/bidders")
BIDDER_FILES = {
    "A": DATASET_ROOT / "Bidder_A_Low_Risk" / "mock_portal_data.json",
    "B": DATASET_ROOT / "Bidder_B_High_Risk" / "mock_portal_data.json",
    "C": DATASET_ROOT / "Bidder_C_Critical_Risk" / "mock_portal_data.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_common(bundle: VerificationEvidenceBundle, bidder_id: str) -> None:
    require(bundle.dataset_id == "SIH26100-T01", "unexpected dataset_id")
    require(bundle.bidder_id == bidder_id, f"unexpected bidder_id: {bundle.bidder_id}")
    require(bundle.synthetic is True, "bundle is not marked synthetic")
    require(not bundle.unknown_sources, "unexpected unknown source records")
    require(bundle.gst is not None, "GST source is missing")
    require(bundle.pan is not None, "PAN source is missing")
    require(bundle.epfo is not None, "EPFO source is missing")
    require(bundle.esic is not None, "ESIC source is missing")
    require(bundle.debarment is not None, "debarment source is missing")
    require(bundle.oem_authorization is not None, "OEM source is missing")
    require(bundle.local_content is not None, "local-content source is missing")
    require(bundle.product_datasheet is not None, "datasheet source is missing")
    require(bundle.issuer_verification is not None, "issuer source is missing")
    require(bundle.emd is not None, "EMD source is missing")


def validate_bidder_a(bundle: VerificationEvidenceBundle) -> None:
    validate_common(bundle, "BIDDER_A")
    assert bundle.gst and bundle.pan and bundle.epfo and bundle.esic
    assert bundle.nsic and bundle.debarment and bundle.oem_authorization
    assert bundle.local_content and bundle.product_datasheet
    assert bundle.issuer_verification and bundle.emd
    require(bundle.gst.status == "ACTIVE", "A GST status mismatch")
    require(bundle.gst.latest_return_period == "2026-08", "A GST period mismatch")
    require(bundle.pan.pan_reference == "SYNTH0001A", "A PAN mismatch")
    require(bundle.pan.status == "VALID", "A PAN status mismatch")
    require(bundle.epfo.compliant_through == "2026-08", "A EPFO period mismatch")
    require(bundle.epfo.payment_date == date(2026, 9, 14), "A EPFO payment mismatch")
    require(bundle.epfo.outstanding_amount == Decimal("0"), "A EPFO balance mismatch")
    require(bundle.esic.registration_status == "ACTIVE", "A ESIC status mismatch")
    require(bundle.nsic.registration_number == "NSIC/SPR/SYN/2026/0001", "A NSIC mismatch")
    require(bundle.debarment.active is False, "A debarment mismatch")
    require(bundle.oem_authorization.valid_through == date(2027, 3, 31), "A OEM validity mismatch")
    require(bundle.local_content.verified_local_content_percentage == 62.0, "A local content mismatch")
    require(len(bundle.product_datasheet.technical_specifications) == 14, "A technical specifications mismatch")
    require(len(bundle.issuer_verification.records) == 3, "A experience records mismatch")
    require(bundle.emd.evidence_type == "EXEMPTION", "A EMD type mismatch")


def validate_bidder_b(bundle: VerificationEvidenceBundle) -> None:
    validate_common(bundle, "BIDDER_B")
    assert bundle.gst and bundle.epfo and bundle.dpiit
    assert bundle.debarment and bundle.oem_authorization and bundle.emd
    require(bundle.gst.status == "ACTIVE", "B GST status mismatch")
    require(bundle.epfo.contribution_state == "OVERDUE", "B EPFO state mismatch")
    require(bundle.epfo.payment_status == "UNPAID", "B EPFO payment status mismatch")
    require(bundle.epfo.latest_due_period == "2026-08", "B EPFO period mismatch")
    require(bundle.epfo.due_date == date(2026, 9, 15), "B EPFO due date mismatch")
    require(bundle.epfo.payment_date is None, "B EPFO payment date should be absent")
    require(bundle.epfo.outstanding_amount == Decimal("396000"), "B EPFO balance mismatch")
    require(bundle.epfo.portal_document_match is False, "B portal/document match mismatch")
    require(bundle.oem_authorization.valid_through == date(2027, 1, 25), "B OEM validity mismatch")
    require(bundle.oem_authorization.validity_shortfall_days == 25, "B OEM shortfall mismatch")
    require(bundle.dpiit.recognition_number == "DPIIT/SYN/STARTUP/2024/0002", "B DPIIT mismatch")
    require(bundle.debarment.active is False, "B debarment mismatch")
    require(bundle.emd.evidence_type == "PAYMENT", "B EMD type mismatch")
    require(bundle.emd.payment_status == "PAID", "B EMD payment mismatch")


def validate_bidder_c(bundle: VerificationEvidenceBundle) -> None:
    validate_common(bundle, "BIDDER_C")
    assert bundle.gst and bundle.pan and bundle.esic
    assert bundle.debarment and bundle.local_content
    assert bundle.oem_authorization and bundle.product_datasheet
    require(bundle.gst.status == "CANCELLED", "C GST status mismatch")
    require(bundle.gst.cancellation_date == date(2026, 7, 15), "C GST cancellation mismatch")
    require(bundle.gst.missing_return_periods == ["2026-07", "2026-08"], "C missing returns mismatch")
    require(bundle.pan.pan_reference == "SYNTH0093X", "C authoritative PAN mismatch")
    require(bundle.pan.uploaded_pan_reference == "SYNTH0003C", "C uploaded PAN mismatch")
    require(bundle.pan.identity_match == "MATERIAL_MISMATCH", "C PAN identity mismatch")
    require(bundle.esic.status_at_bid_close == "INACTIVE_DEFAULTING", "C ESIC bid-close state mismatch")
    require(bundle.esic.contribution_state == "DEFAULTING", "C ESIC contribution state mismatch")
    require(bundle.esic.outstanding_amount == Decimal("116800"), "C ESIC balance mismatch")
    require(bundle.local_content.verified_local_content_percentage == 32.0, "C local content mismatch")
    require(bundle.debarment.active is True, "C active debarment mismatch")
    require(bundle.debarment.order_reference == "SYN-DEBAR-KRV-2026-031", "C debarment order mismatch")
    require(bundle.oem_authorization.document_present is False, "C OEM document-present mismatch")
    require(bundle.oem_authorization.authorization_number is None, "C OEM authorization should be absent")
    require(
        bundle.product_datasheet.failed_technical_requirements
        == ["TECH-001B", "TECH-001D", "TECH-001H"],
        "C failed technical requirement IDs mismatch",
    )


def print_summary(label: str, bundle: VerificationEvidenceBundle) -> None:
    assert bundle.gst and bundle.pan and bundle.epfo and bundle.esic
    assert bundle.debarment and bundle.oem_authorization
    print(f"BIDDER {label}")
    print(f"GST registry status: {bundle.gst.status}")
    print(f"PAN registry reference: {bundle.pan.pan_reference}")
    print(
        "EPFO latest period/payment state: "
        f"{bundle.epfo.latest_period} / "
        f"{bundle.epfo.payment_status or 'FACTS_RECORDED'}"
    )
    print(
        "ESIC status/balance: "
        f"{bundle.esic.status_at_bid_close or bundle.esic.registration_status} / "
        f"{bundle.esic.outstanding_amount}"
    )
    print(
        "OEM authorization valid through: "
        f"{bundle.oem_authorization.valid_through}"
    )
    print(f"Debarment active: {bundle.debarment.active}")
    print(
        "Unknown sources: "
        f"{', '.join(bundle.unknown_sources) if bundle.unknown_sources else 'none'}"
    )
    print()


def validate_error_and_unknown_handling(
    loader: MockVerificationLoader,
    source_file: Path,
) -> None:
    try:
        loader.load(source_file.with_name("missing_mock_portal_data.json"))
    except MockVerificationFileNotFoundError:
        pass
    else:
        raise AssertionError("missing source file did not raise the expected error")

    with TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        malformed_path = temporary_root / "malformed.json"
        malformed_path.write_text("{not valid json", encoding="utf-8")
        try:
            loader.load(malformed_path)
        except MockVerificationValidationError:
            pass
        else:
            raise AssertionError("malformed JSON did not raise the expected error")

        source_payload = json.loads(source_file.read_text(encoding="utf-8"))
        future_record = {
            "source_system": "FUTURE_SOURCE",
            "response": {"factual_value": 42},
        }
        source_payload["records"]["future_source"] = future_record
        future_path = temporary_root / "future.json"
        future_path.write_text(json.dumps(source_payload), encoding="utf-8")
        future_bundle = loader.load(future_path)
        require(
            future_bundle.unknown_sources["future_source"] == future_record,
            "unknown source record was not preserved",
        )


def main() -> int:
    loader = MockVerificationLoader()
    validators = {
        "A": validate_bidder_a,
        "B": validate_bidder_b,
        "C": validate_bidder_c,
    }

    try:
        for label, source_file in BIDDER_FILES.items():
            bundle = loader.load(source_file)
            validators[label](bundle)
            print_summary(label, bundle)
        validate_error_and_unknown_handling(loader, BIDDER_FILES["A"])
    except (
        MockVerificationFileNotFoundError,
        MockVerificationValidationError,
        AssertionError,
    ) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print("PASS: all mock verification loader assertions passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
