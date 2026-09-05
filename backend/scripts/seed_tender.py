from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, date
from pathlib import Path

import oracledb
from pypdf import PdfReader

from script_config import DATA_ROOT, oracle_connection_kwargs


# ============================================================
# PATHS
# ============================================================

TENDER_JSON = DATA_ROOT / "config" / "tender_requirements.json"
SCORING_JSON = DATA_ROOT / "config" / "scoring_rules.json"

TENDER_DIR = DATA_ROOT / "tender"
ATTACHMENTS_DIR = TENDER_DIR / "attachments"


# ============================================================
# HELPERS
# ============================================================

def stable_uuid(*parts: str) -> str:
    """
    Deterministic UUID for repeatable synthetic dataset seeding.
    """
    value = "::".join(str(p) for p in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def pdf_page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    return datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    ).date()


def parse_timestamp(value):
    if not value:
        return None

    return datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )


def document_code_from_name(name: str) -> str:
    if name == "tender.pdf":
        return "TENDER-MAIN"

    return name.split("_", 1)[0]


def document_type_from_name(name: str) -> str:
    mapping = {
        "tender.pdf": "MAIN_TENDER",
        "T01_Buyer_Technical_Specifications.pdf":
            "BUYER_TECHNICAL_SPECIFICATIONS",
        "T02_Bidder_Compliance_Checklist_and_Formats.pdf":
            "BIDDER_COMPLIANCE_CHECKLIST",
        "T03_OEM_Authorization_Format.pdf":
            "OEM_AUTHORIZATION_FORMAT",
        "T04_Local_Content_Declaration_Format.pdf":
            "LOCAL_CONTENT_DECLARATION_FORMAT",
        "T07_Buyer_Added_Bid_Specific_ATC.pdf":
            "BUYER_ADDED_ATC",
    }

    return mapping.get(name, "TENDER_ATTACHMENT")


# ============================================================
# SEED
# ============================================================

def main():
    print("====================================================")
    print(" BIDGUARD AI - TENDER SEED")
    print("====================================================")

    tender_config = load_json(TENDER_JSON)
    scoring_config = load_json(SCORING_JSON)

    dataset_id = tender_config["dataset_id"]
    tender = tender_config["tender"]
    buyer = tender["buyer"]

    print(f"Dataset: {dataset_id}")
    print(f"Bid:     {tender['bid_number']}")

    connection = oracledb.connect(**oracle_connection_kwargs())

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # PRE-SEED SAFETY CHECK
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM tenders
            WHERE dataset_id = :dataset_id
            """,
            dataset_id=dataset_id,
        )

        existing = cursor.fetchone()

        if existing:
            existing_tender_id = existing[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM bid_submissions
                WHERE tender_id = :tender_id
                """,
                tender_id=existing_tender_id,
            )

            submission_count = cursor.fetchone()[0]

            if submission_count > 0:
                raise RuntimeError(
                    "Tender already has bid submissions. "
                    "Seed script will not overwrite it."
                )

            print(
                "Existing seed tender found. "
                "Replacing tender-side synthetic data..."
            )

            cursor.execute(
                """
                DELETE FROM tenders
                WHERE id = :id
                """,
                id=existing_tender_id,
            )

        # ----------------------------------------------------
        # IDS
        # ----------------------------------------------------

        buyer_id = stable_uuid(dataset_id, "BUYER")
        tender_id = stable_uuid(dataset_id, "TENDER")

        # ----------------------------------------------------
        # BUYER
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM buyers
            WHERE id = :id
            """,
            id=buyer_id,
        )

        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO buyers (
                    id,
                    name,
                    ministry,
                    department,
                    organisation,
                    office,
                    address,
                    is_synthetic
                )
                VALUES (
                    :id,
                    :name,
                    :ministry,
                    :department,
                    :organisation,
                    :office,
                    :address,
                    1
                )
                """,
                id=buyer_id,
                name=buyer["organisation"],
                ministry=buyer["ministry"],
                department=buyer["department"],
                organisation=buyer["organisation"],
                office=buyer["office"],
                address=buyer["address"],
            )

        # ----------------------------------------------------
        # TENDER
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO tenders (
                id,
                buyer_id,
                dataset_id,
                bid_number,
                title,
                category,
                quantity,
                estimated_value_inr,
                bid_date,
                bid_end_at,
                bid_opening_at,
                offer_validity_days,
                offer_valid_through,
                oem_authorization_required_through,
                delivery_days,
                installation_days,
                warranty_years,
                evaluation_method,
                status,
                human_final_decision_required,
                is_synthetic
            )
            VALUES (
                :id,
                :buyer_id,
                :dataset_id,
                :bid_number,
                :title,
                :category,
                :quantity,
                :estimated_value,
                :bid_date,
                :bid_end_at,
                :bid_opening_at,
                :offer_validity_days,
                :offer_valid_through,
                :oem_required_through,
                :delivery_days,
                :installation_days,
                :warranty_years,
                :evaluation_method,
                :status,
                1,
                1
            )
            """,
            id=tender_id,
            buyer_id=buyer_id,
            dataset_id=dataset_id,
            bid_number=tender["bid_number"],
            title=tender["title"],
            category=tender["category"],
            quantity=tender["quantity"],
            estimated_value=tender["estimated_value_inr"],
            bid_date=parse_date(tender["bid_date"]),
            bid_end_at=parse_timestamp(tender["bid_end_at"]),
            bid_opening_at=parse_timestamp(
                tender["bid_opening_at"]
            ),
            offer_validity_days=tender["offer_validity_days"],
            offer_valid_through=parse_date(
                tender["offer_valid_through"]
            ),
            oem_required_through=parse_date(
                tender["oem_authorization_required_through"]
            ),
            delivery_days=tender["delivery_days"],
            installation_days=tender[
                "installation_days_after_delivery"
            ],
            warranty_years=tender["warranty_years"],
            evaluation_method=tender["evaluation_method"],
            status="SYNTHETIC_TEST",
        )

        # ----------------------------------------------------
        # TENDER REQUIREMENTS - 16
        # ----------------------------------------------------

        mandatory_prefixes = {
            "MANDATORY",
            "MANDATORY_WITH_TENDER_SPECIFIC_RELAXATION",
            "MANDATORY_PAYMENT_OR_CONDITIONAL_EXEMPTION",
        }

        requirement_count = 0

        for requirement in tender_config["requirements"]:
            requirement_id = stable_uuid(
                dataset_id,
                "REQUIREMENT",
                requirement["requirement_id"],
            )

            applicability = requirement.get(
                "applicability",
                "MANDATORY",
            )

            is_mandatory = 1 if any(
                applicability.startswith(prefix)
                for prefix in mandatory_prefixes
            ) else 0

            cursor.execute(
                """
                INSERT INTO tender_requirements (
                    id,
                    tender_id,
                    requirement_code,
                    title,
                    description,
                    weight,
                    severity,
                    applicability,
                    is_mandatory,
                    active
                )
                VALUES (
                    :id,
                    :tender_id,
                    :code,
                    :title,
                    :description,
                    :weight,
                    :severity,
                    :applicability,
                    :is_mandatory,
                    1
                )
                """,
                id=requirement_id,
                tender_id=tender_id,
                code=requirement["requirement_id"],
                title=requirement["title"],
                description=requirement["description"],
                weight=requirement["weight"],
                severity=requirement["severity"],
                applicability=applicability,
                is_mandatory=is_mandatory,
            )

            requirement_count += 1

        # ----------------------------------------------------
        # TECHNICAL REQUIREMENTS - 14
        # ----------------------------------------------------

        technical_count = 0

        for spec in tender_config["technical_specifications"]:
            technical_id = stable_uuid(
                dataset_id,
                "TECHNICAL",
                spec["technical_id"],
            )

            cursor.execute(
                """
                INSERT INTO technical_requirements (
                    id,
                    tender_id,
                    technical_code,
                    parameter_name,
                    minimum_requirement,
                    classification
                )
                VALUES (
                    :id,
                    :tender_id,
                    :technical_code,
                    :parameter_name,
                    :minimum_requirement,
                    :classification
                )
                """,
                id=technical_id,
                tender_id=tender_id,
                technical_code=spec["technical_id"],
                parameter_name=spec["parameter"],
                minimum_requirement=spec["minimum_requirement"],
                classification=spec["classification"],
            )

            technical_count += 1

        # ----------------------------------------------------
        # BUYER ADDED TERMS - 16
        # ----------------------------------------------------

        term_count = 0

        for term in tender_config["buyer_added_terms"]:
            term_id = stable_uuid(
                dataset_id,
                "TERM",
                term["term_id"],
            )

            cursor.execute(
                """
                INSERT INTO tender_terms (
                    id,
                    tender_id,
                    term_code,
                    term_text
                )
                VALUES (
                    :id,
                    :tender_id,
                    :term_code,
                    :term_text
                )
                """,
                id=term_id,
                tender_id=tender_id,
                term_code=term["term_id"],
                term_text=term["text"],
            )

            term_count += 1

        # ----------------------------------------------------
        # TENDER DOCUMENT REFERENCES
        # ----------------------------------------------------

        document_paths = [
            TENDER_DIR / "tender.pdf",
            ATTACHMENTS_DIR /
                "T01_Buyer_Technical_Specifications.pdf",
            ATTACHMENTS_DIR /
                "T02_Bidder_Compliance_Checklist_and_Formats.pdf",
            ATTACHMENTS_DIR /
                "T03_OEM_Authorization_Format.pdf",
            ATTACHMENTS_DIR /
                "T04_Local_Content_Declaration_Format.pdf",
            ATTACHMENTS_DIR /
                "T07_Buyer_Added_Bid_Specific_ATC.pdf",
        ]

        document_count = 0

        for document_path in document_paths:
            if not document_path.exists():
                raise FileNotFoundError(
                    f"Tender document missing: {document_path}"
                )

            document_id = stable_uuid(
                dataset_id,
                "TENDER_DOCUMENT",
                document_path.name,
            )

            cursor.execute(
                """
                INSERT INTO tender_documents (
                    id,
                    tender_id,
                    document_code,
                    document_type,
                    file_name,
                    storage_path,
                    sha256,
                    page_count
                )
                VALUES (
                    :id,
                    :tender_id,
                    :document_code,
                    :document_type,
                    :file_name,
                    :storage_path,
                    :sha256,
                    :page_count
                )
                """,
                id=document_id,
                tender_id=tender_id,
                document_code=document_code_from_name(
                    document_path.name
                ),
                document_type=document_type_from_name(
                    document_path.name
                ),
                file_name=document_path.name,
                storage_path=str(document_path),
                sha256=sha256_file(document_path),
                page_count=pdf_page_count(document_path),
            )

            document_count += 1

        # ----------------------------------------------------
        # VERIFICATION SOURCES
        # ----------------------------------------------------

        sources = set()

        for requirement in tender_config["requirements"]:
            for source in requirement.get(
                "authoritative_sources",
                [],
            ):
                sources.add(source)

        source_count = 0

        for source_code in sorted(sources):
            source_id = stable_uuid(
                dataset_id,
                "SOURCE",
                source_code,
            )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM verification_sources
                WHERE source_code = :source_code
                """,
                source_code=source_code,
            )

            if cursor.fetchone()[0] > 0:
                continue

            is_synthetic = 1

            source_type = (
                "MOCK_REGISTRY"
                if source_code.startswith("MOCK_")
                else "SYNTHETIC_VERIFICATION"
            )

            cursor.execute(
                """
                INSERT INTO verification_sources (
                    id,
                    source_code,
                    source_name,
                    source_type,
                    is_synthetic,
                    active
                )
                VALUES (
                    :id,
                    :source_code,
                    :source_name,
                    :source_type,
                    :is_synthetic,
                    1
                )
                """,
                id=source_id,
                source_code=source_code,
                source_name=source_code.replace("_", " ").title(),
                source_type=source_type,
                is_synthetic=is_synthetic,
            )

            source_count += 1

        # ----------------------------------------------------
        # VALIDATION AGAINST SCORING CONFIG
        # ----------------------------------------------------

        expected_weights = scoring_config[
            "requirement_weights"
        ]

        configured_total = sum(expected_weights.values())

        if configured_total != 100:
            raise RuntimeError(
                f"Configured weight is {configured_total}, expected 100"
            )

        json_requirement_ids = {
            r["requirement_id"]
            for r in tender_config["requirements"]
        }

        scoring_requirement_ids = set(
            expected_weights.keys()
        )

        if json_requirement_ids != scoring_requirement_ids:
            raise RuntimeError(
                "Requirement IDs differ between "
                "tender_requirements.json and scoring_rules.json"
            )

        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

        connection.commit()

        print()
        print("====================================================")
        print(" SEED COMPLETE")
        print("====================================================")
        print(f"Buyer:                  1")
        print(f"Tender:                 1")
        print(f"Tender documents:       {document_count}")
        print(f"Compliance requirements:{requirement_count}")
        print(f"Technical requirements: {technical_count}")
        print(f"ATC terms:              {term_count}")
        print(f"Verification sources:   {source_count}")
        print(f"Configured weight:      {configured_total}")
        print()
        print("PASS: Tender seed committed to Oracle.")

    except Exception as exc:
        connection.rollback()

        print()
        print("SEED FAILED")
        print(str(exc))
        print()
        print("Transaction rolled back.")

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
