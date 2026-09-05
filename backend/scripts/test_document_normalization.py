from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.core.config import get_settings
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
from app.services.document_processing.azure_document_intelligence import (
    AzureDocumentIntelligenceService,
    DocumentExtractionError,
)
from app.services.document_processing.document_normalizer import (
    DocumentNormalizer,
)
from app.services.document_processing.normalizers.base import (
    DocumentNormalizationError,
)


DEFAULT_DOCUMENT_DIRECTORY = Path(
    "/home/tarun/TARUN/projects/test-sih-docs/"
    "bidders/Bidder_A_Low_Risk/documents"
)
DEFAULT_DOCUMENTS = (
    DEFAULT_DOCUMENT_DIRECTORY / "03_PAN_Record_Reference.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "09_OEM_Authorization_Letter.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "10_Offered_Model_Product_Datasheet.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "02_GST_Registration_Certificate.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "04_Udyam_Registration_Certificate.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "05_EPFO_Registration_Letter.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "06_EPFO_Contribution_Status_Aug_2026.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "07_ESIC_C11_Registration_Letter.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "08_ESIC_Contribution_Status_Aug_2026.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "12_CA_Average_Turnover_Certificate.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "13_Audited_Financial_Extracts_FY2022_25.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "14_Similar_Experience_Evidence_Bundle.pdf",
    DEFAULT_DOCUMENT_DIRECTORY
    / "15_Local_Content_Declaration_and_CA_Certificate.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "16_Technical_Compliance_Sheet.pdf",
    DEFAULT_DOCUMENT_DIRECTORY
    / "17_Warranty_SLA_and_No_Cloud_Upload_Undertaking.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "18_EMD_Exemption_Proof.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "19_Financial_Bid_BOQ.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "20_No_Blacklisting_Self_Declaration.pdf",
    DEFAULT_DOCUMENT_DIRECTORY / "21_NSIC_SPR_Certificate.pdf",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract and normalize supported BidGuard bidder PDFs."
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        type=Path,
        help=(
            "Optional single PDF. When omitted, all supported Bidder A "
            "documents are tested."
        ),
    )
    return parser.parse_args()


def require(condition: bool, message: str, source_file: str) -> None:
    if not condition:
        raise AssertionError(f"{source_file}: {message}")


def require_fields(document, expectations: dict[str, tuple[object, object]]) -> None:
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )


def validate_pan(document: PanRecordDocument) -> None:
    fields = document.fields
    require(
        fields.pan_reference == "SYNTH0001A",
        f"unexpected pan_reference: {fields.pan_reference!r}",
        document.source_file,
    )
    require(
        bool(fields.legal_name and "averonix" in fields.legal_name.casefold()),
        "legal_name does not contain Averonix",
        document.source_file,
    )
    require(
        fields.identity_status == "VALID",
        f"unexpected identity_status: {fields.identity_status!r}",
        document.source_file,
    )


def validate_oem(document: OemAuthorizationDocument) -> None:
    fields = document.fields
    require(
        fields.authorization_number == "NITPL/SYN-AUTH/2026/0042",
        f"unexpected authorization_number: {fields.authorization_number!r}",
        document.source_file,
    )
    require(
        fields.valid_through == date(2027, 3, 31),
        f"unexpected valid_through: {fields.valid_through!r}",
        document.source_file,
    )
    require(
        bool(
            fields.authorized_bidder
            and "averonix" in fields.authorized_bidder.casefold()
        ),
        "authorized_bidder does not contain Averonix",
        document.source_file,
    )
    require(
        fields.bidder_pan == "SYNTH0001A",
        f"unexpected bidder_pan: {fields.bidder_pan!r}",
        document.source_file,
    )
    require(
        bool(
            fields.offered_brand_model
            and "nx-4600" in fields.offered_brand_model.casefold()
        ),
        "offered_brand_model does not contain NX-4600",
        document.source_file,
    )
    require(
        fields.sku == "NX4600-GOV-SYN",
        f"unexpected sku: {fields.sku!r}",
        document.source_file,
    )


def validate_datasheet(document: ProductDatasheetDocument) -> None:
    fields = document.fields
    expectations = {
        "model": (fields.model, "ScanSphere NX-4600"),
        "sku": (fields.sku, "NX4600-GOV-SYN"),
        "scanning_speed_ppm": (fields.scanning_speed_ppm, 52),
        "duplex_speed_ipm": (fields.duplex_speed_ipm, 104),
        "optical_resolution_dpi": (fields.optical_resolution_dpi, 600),
        "adf_capacity_sheets": (fields.adf_capacity_sheets, 100),
        "recommended_daily_volume_pages": (
            fields.recommended_daily_volume_pages,
            8000,
        ),
    }
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )
    require(
        bool(fields.network and "gigabit ethernet" in fields.network.casefold()),
        "network does not contain Gigabit Ethernet",
        document.source_file,
    )


def validate_gst(document: GstRegistrationDocument) -> None:
    fields = document.fields
    expectations = {
        "gstin": (fields.gstin, "00SYNTH0001A1ZX"),
        "pan_reference": (fields.pan_reference, "SYNTH0001A"),
        "effective_registration_date": (
            fields.effective_registration_date,
            date(2021, 1, 12),
        ),
        "registration_status": (fields.registration_status, "ACTIVE"),
        "document_reference": (
            fields.document_reference,
            "SYN-GST-CERT-AVX-2021-001",
        ),
    }
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )
    require(
        bool(fields.legal_name and "averonix" in fields.legal_name.casefold()),
        "legal_name does not contain Averonix",
        document.source_file,
    )


def validate_udyam(document: UdyamRegistrationDocument) -> None:
    fields = document.fields
    expectations = {
        "udyam_number": (fields.udyam_number, "UDYAM-ZZ-00-0000001"),
        "pan_reference": (fields.pan_reference, "SYNTH0001A"),
        "gstin": (fields.gstin, "00SYNTH0001A1ZX"),
        "registration_date": (fields.registration_date, date(2021, 2, 3)),
        "status": (fields.status, "VALID"),
    }
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )
    require(
        bool(
            fields.enterprise_name
            and "averonix" in fields.enterprise_name.casefold()
        ),
        "enterprise_name does not contain Averonix",
        document.source_file,
    )
    require(
        len(fields.registered_activities) == 3,
        f"expected 3 registered activities, received {fields.registered_activities!r}",
        document.source_file,
    )


def validate_epfo_registration(document: EpfoRegistrationDocument) -> None:
    fields = document.fields
    expectations = {
        "establishment_id": (
            fields.establishment_id,
            "SYNTH/EPFO/AVX/000101",
        ),
        "pan_reference": (fields.pan_reference, "SYNTH0001A"),
        "registration_date": (fields.registration_date, date(2021, 2, 1)),
        "coverage_status": (fields.coverage_status, "ACTIVE"),
        "document_reference": (
            fields.document_reference,
            "SYN-EPFO-REG-AVX-2021-101",
        ),
    }
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )


def validate_epfo_contribution(
    document: EpfoContributionStatusDocument,
) -> None:
    fields = document.fields
    expectations = {
        "pan_reference": (fields.pan_reference, "SYNTH0001A"),
        "latest_compliance_period": (
            fields.latest_compliance_period,
            "August 2026",
        ),
        "statutory_due_date": (
            fields.statutory_due_date,
            date(2026, 9, 15),
        ),
        "payment_date": (fields.payment_date, date(2026, 9, 14)),
        "employee_count": (fields.employee_count, 72),
        "employer_share_amount": (
            fields.employer_share_amount,
            Decimal("259200.00"),
        ),
        "outstanding_amount": (fields.outstanding_amount, Decimal("0.00")),
        "payment_reference": (
            fields.payment_reference,
            "SYN-EPFO-PAY-20260914-0041",
        ),
    }
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )


def validate_esic_registration(document: EsicRegistrationDocument) -> None:
    fields = document.fields
    expectations = {
        "employer_code": (
            fields.employer_code,
            "SYN-ESIC-00-000000001",
        ),
        "pan_reference": (fields.pan_reference, "SYNTH0001A"),
        "registration_date": (fields.registration_date, date(2021, 2, 1)),
        "coverage_status": (fields.coverage_status, "ACTIVE"),
        "document_reference": (
            fields.document_reference,
            "SYN-ESIC-C11-AVX-2021-001",
        ),
    }
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )


def validate_esic_contribution(
    document: EsicContributionStatusDocument,
) -> None:
    fields = document.fields
    expectations = {
        "pan_reference": (fields.pan_reference, "SYNTH0001A"),
        "latest_compliance_period": (
            fields.latest_compliance_period,
            "August 2026",
        ),
        "statutory_due_date": (
            fields.statutory_due_date,
            date(2026, 9, 15),
        ),
        "payment_date": (fields.payment_date, date(2026, 9, 14)),
        "covered_employee_count": (fields.covered_employee_count, 36),
        "contribution_amount": (
            fields.contribution_amount,
            Decimal("46400.00"),
        ),
        "outstanding_amount": (fields.outstanding_amount, Decimal("0.00")),
        "registration_status": (fields.registration_status, "ACTIVE"),
        "challan_reference": (
            fields.challan_reference,
            "SYN-ESIC-CHL-20260914-0036",
        ),
    }
    for field_name, (actual, expected) in expectations.items():
        require(
            actual == expected,
            f"expected {field_name}={expected!r}, received {actual!r}",
            document.source_file,
        )


def validate_turnover(document: TurnoverCertificateDocument) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "pan_reference": (fields.pan_reference, "SYNTH0001A"),
            "average_turnover": (
                fields.average_turnover,
                Decimal("84000000"),
            ),
            "certificate_date": (
                fields.certificate_date,
                date(2026, 9, 10),
            ),
            "professional_name": (fields.professional_name, "Kavian Merel"),
        },
    )
    require_fields(
        document,
        {
            "financial_years": (
                [item.financial_year for item in fields.financial_years],
                ["FY 2022-23", "FY 2023-24", "FY 2024-25"],
            ),
            "turnover_values": (
                [item.turnover for item in fields.financial_years],
                [
                    Decimal("78000000"),
                    Decimal("84000000"),
                    Decimal("90000000"),
                ],
            ),
        },
    )


def validate_audited_financials(document: AuditedFinancialsDocument) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "pan_reference": (fields.pan_reference, "SYNTH0001A"),
            "average_turnover": (
                fields.average_turnover,
                Decimal("84000000"),
            ),
            "financial_year_count": (len(fields.financial_years), 3),
            "revenues": (
                [item.revenue_from_operations for item in fields.financial_years],
                [
                    Decimal("78000000.00"),
                    Decimal("84000000.00"),
                    Decimal("90000000.00"),
                ],
            ),
            "audit_references": (
                [item.audit_reference for item in fields.financial_years],
                [
                    "SYN-AUD-AVX-202223",
                    "SYN-AUD-AVX-202324",
                    "SYN-AUD-AVX-202425",
                ],
            ),
        },
    )


def validate_similar_experience(document: SimilarExperienceDocument) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "pan_reference": (fields.pan_reference, "SYNTH0001A"),
            "experience_years": (fields.experience_years, 5.8),
            "record_count": (len(fields.records), 3),
        },
    )
    first_record = fields.records[0]
    require_fields(
        document,
        {
            "first_work_order": (
                first_record.work_order_number,
                "SYN-WO-ALPHA-2023-011",
            ),
            "first_customer": (
                first_record.customer,
                "Heliovar Records Services Corporation - Fictional",
            ),
            "first_quantity": (first_record.quantity, 90),
            "first_completion_date": (
                first_record.completion_date,
                date(2024, 1, 20),
            ),
        },
    )


def validate_local_content(document: LocalContentDocument) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "pan_reference": (fields.pan_reference, "SYNTH0001A"),
            "offered_model": (
                fields.offered_model,
                "Novacrest ScanSphere NX-4600",
            ),
            "local_content_percentage": (
                fields.local_content_percentage,
                62.0,
            ),
            "domestic_value": (fields.domestic_value, Decimal("62")),
            "total_value": (fields.total_value, Decimal("100")),
            "certificate_date": (
                fields.certificate_date,
                date(2026, 9, 11),
            ),
            "component_count": (len(fields.components), 10),
        },
    )


def validate_technical_compliance(
    document: TechnicalComplianceMatrixDocument,
) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "model": (fields.model, "ScanSphere NX-4600"),
            "sku": (fields.sku, "NX4600-GOV-SYN"),
            "technical_row_count": (len(fields.rows), 14),
            "technical_codes": (
                [row.technical_code for row in fields.rows],
                [f"TECH-001{suffix}" for suffix in "ABCDEFGHIJKLMN"],
            ),
        },
    )
    rows = {row.technical_code: row for row in fields.rows}
    require_fields(
        document,
        {
            "TECH-001A offered specification": (
                rows["TECH-001A"].offered_specification,
                "A4 sheet-fed duplex document scanner",
            ),
            "TECH-001N offered specification": (
                rows["TECH-001N"].offered_specification,
                "Local/offline scanning; no mandatory external-cloud upload",
            ),
        },
    )


def validate_warranty_sla(document: WarrantySlaUndertakingDocument) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "offered_model": (
                fields.offered_model,
                "Novacrest ScanSphere NX-4600",
            ),
            "warranty_years": (fields.warranty_years, 3),
            "onsite_warranty": (fields.onsite_warranty, True),
            "minimum_uptime_percentage": (
                fields.minimum_uptime_percentage,
                95.0,
            ),
            "no_cloud_upload": (fields.no_cloud_upload, True),
            "local_processing_commitment": (
                fields.local_processing_commitment,
                True,
            ),
            "undertaking_date": (
                fields.undertaking_date,
                date(2026, 9, 15),
            ),
        },
    )


def validate_emd(document: EmdEvidenceDocument) -> None:
    fields = document.fields
    if fields.evidence_type == "EXEMPTION_CLAIM":
        require_fields(
            document,
            {
                "amount": (fields.amount, Decimal("400000")),
                "exemption_claimed": (fields.exemption_claimed, True),
                "claim_date": (fields.claim_date, date(2026, 9, 15)),
                "udyam_reference": (
                    fields.udyam_reference,
                    "UDYAM-ZZ-00-0000001",
                ),
                "nsic_reference": (
                    fields.nsic_reference,
                    "NSIC/SPR/SYN/2026/0001",
                ),
            },
        )
        return
    if fields.evidence_type == "EXEMPTION_SUPPORT":
        require_fields(
            document,
            {
                "certificate_reference": (
                    fields.certificate_reference,
                    "SYN-NSIC-CERT-AVX-2026-0001",
                ),
                "nsic_reference": (
                    fields.nsic_reference,
                    "NSIC/SPR/SYN/2026/0001",
                ),
                "valid_through": (fields.valid_through, date(2028, 3, 31)),
                "monetary_limit": (
                    fields.monetary_limit,
                    Decimal("120000000"),
                ),
                "category_count": (len(fields.covered_categories), 3),
            },
        )
        return
    raise AssertionError(
        f"{document.source_file}: unexpected EMD evidence type "
        f"{fields.evidence_type!r}"
    )


def validate_financial_boq(document: FinancialBoqDocument) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "currency": (fields.currency, "Indian Rupees"),
            "line_item_count": (len(fields.line_items), 4),
            "total_taxable_value": (
                fields.total_taxable_value,
                Decimal("39780000.00"),
            ),
            "taxes": (fields.taxes, Decimal("7160400.00")),
            "tax_percentage": (fields.tax_percentage, 18.0),
            "total_bid_value": (
                fields.total_bid_value,
                Decimal("46940400.00"),
            ),
        },
    )
    first_item = fields.line_items[0]
    require_fields(
        document,
        {
            "first_quantity": (first_item.quantity, Decimal("180")),
            "first_unit_rate": (
                first_item.unit_rate,
                Decimal("218000.00"),
            ),
            "first_line_total": (
                first_item.line_total,
                Decimal("39240000.00"),
            ),
        },
    )


def validate_no_blacklisting(
    document: NoBlacklistingDeclarationDocument,
) -> None:
    fields = document.fields
    require_fields(
        document,
        {
            "pan_reference": (fields.pan_reference, "SYNTH0001A"),
            "declaration_status": (
                fields.declaration_status,
                "NO ACTIVE BLACKLISTING OR DEBARMENT",
            ),
            "declaration_date": (
                fields.declaration_date,
                date(2026, 9, 15),
            ),
            "signatory_name": (fields.signatory_name, "Ira Velnor"),
            "signatory_role": (fields.signatory_role, "Director - Commercial"),
        },
    )


def validate_document(document) -> None:
    if isinstance(document, PanRecordDocument):
        validate_pan(document)
        return
    if isinstance(document, OemAuthorizationDocument):
        validate_oem(document)
        return
    if isinstance(document, ProductDatasheetDocument):
        validate_datasheet(document)
        return
    if isinstance(document, GstRegistrationDocument):
        validate_gst(document)
        return
    if isinstance(document, UdyamRegistrationDocument):
        validate_udyam(document)
        return
    if isinstance(document, EpfoRegistrationDocument):
        validate_epfo_registration(document)
        return
    if isinstance(document, EpfoContributionStatusDocument):
        validate_epfo_contribution(document)
        return
    if isinstance(document, EsicRegistrationDocument):
        validate_esic_registration(document)
        return
    if isinstance(document, EsicContributionStatusDocument):
        validate_esic_contribution(document)
        return
    if isinstance(document, TurnoverCertificateDocument):
        validate_turnover(document)
        return
    if isinstance(document, AuditedFinancialsDocument):
        validate_audited_financials(document)
        return
    if isinstance(document, SimilarExperienceDocument):
        validate_similar_experience(document)
        return
    if isinstance(document, LocalContentDocument):
        validate_local_content(document)
        return
    if isinstance(document, TechnicalComplianceMatrixDocument):
        validate_technical_compliance(document)
        return
    if isinstance(document, WarrantySlaUndertakingDocument):
        validate_warranty_sla(document)
        return
    if isinstance(document, EmdEvidenceDocument):
        validate_emd(document)
        return
    if isinstance(document, FinancialBoqDocument):
        validate_financial_boq(document)
        return
    if isinstance(document, NoBlacklistingDeclarationDocument):
        validate_no_blacklisting(document)
        return
    raise AssertionError(
        f"Unexpected normalized model: {type(document).__name__}"
    )


def main() -> int:
    arguments = parse_arguments()
    document_paths = (
        (arguments.pdf_path,) if arguments.pdf_path else DEFAULT_DOCUMENTS
    )
    settings = get_settings()
    normalizer = DocumentNormalizer()

    try:
        with AzureDocumentIntelligenceService(settings) as extraction_service:
            for document_path in document_paths:
                print("=" * 78)
                print(f"Processing: {document_path}")
                print("=" * 78)

                extraction = extraction_service.extract(document_path)
                normalized = normalizer.normalize(extraction)
                validate_document(normalized)

                print(normalized.model_dump_json(indent=2))
                print(
                    f"\nPASS: {normalized.document_type} "
                    "normalization assertions passed.\n"
                )
    except (
        DocumentExtractionError,
        DocumentNormalizationError,
        AssertionError,
    ) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
