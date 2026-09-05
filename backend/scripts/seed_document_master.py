from __future__ import annotations

import json
import uuid
from pathlib import Path

import oracledb

from script_config import DATA_ROOT, oracle_connection_kwargs

DATA_FILE = DATA_ROOT / "config" / "tender_requirements.json"


def stable_uuid(*parts: str) -> str:
    value = "::".join(str(p) for p in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def main():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        config = json.load(f)

    dataset_id = config["dataset_id"]

    conn = oracledb.connect(**oracle_connection_kwargs())

    try:
        cur = conn.cursor()

        # --------------------------------------------------
        # FIND TENDER
        # --------------------------------------------------

        cur.execute(
            """
            SELECT id
            FROM tenders
            WHERE dataset_id = :dataset_id
            """,
            dataset_id=dataset_id,
        )

        row = cur.fetchone()

        if not row:
            raise RuntimeError(
                f"Tender not found for dataset {dataset_id}"
            )

        tender_id = row[0]

        # --------------------------------------------------
        # CLEAR ONLY THIS TENDER'S DOCUMENT CONFIG
        # --------------------------------------------------

        cur.execute(
            """
            DELETE FROM requirement_evidence_rules
            WHERE requirement_id IN (
                SELECT id
                FROM tender_requirements
                WHERE tender_id = :tender_id
            )
            """,
            tender_id=tender_id,
        )

        cur.execute(
            """
            DELETE FROM requirement_document_rules
            WHERE requirement_id IN (
                SELECT id
                FROM tender_requirements
                WHERE tender_id = :tender_id
            )
            """,
            tender_id=tender_id,
        )

        cur.execute(
            """
            DELETE FROM tender_required_documents
            WHERE tender_id = :tender_id
            """,
            tender_id=tender_id,
        )

        # --------------------------------------------------
        # 22 REQUIRED DOCUMENT DEFINITIONS
        # --------------------------------------------------

        document_count = 0

        for doc in config["mandatory_documents"]:
            applicability = doc["applicability"]

            conditional = (
                1
                if applicability.startswith("CONDITIONAL")
                else 0
            )

            mandatory = (
                0
                if conditional
                else 1
            )

            condition_text = (
                applicability
                if conditional
                else None
            )

            cur.execute(
                """
                INSERT INTO tender_required_documents (
                    id,
                    tender_id,
                    document_code,
                    document_name,
                    description,
                    mandatory,
                    conditional,
                    condition_text,
                    active
                )
                VALUES (
                    :id,
                    :tender_id,
                    :document_code,
                    :document_name,
                    :description,
                    :mandatory,
                    :conditional,
                    :condition_text,
                    1
                )
                """,
                id=stable_uuid(
                    dataset_id,
                    "REQUIRED_DOCUMENT",
                    doc["document_id"],
                ),
                tender_id=tender_id,
                document_code=doc["document_id"],
                document_name=doc["document_name"],
                description=(
                    f"Applicability: {applicability}"
                ),
                mandatory=mandatory,
                conditional=conditional,
                condition_text=condition_text,
            )

            document_count += 1

        # --------------------------------------------------
        # REQUIREMENT EVIDENCE RULES
        # --------------------------------------------------

        evidence_count = 0
        requirement_count = 0

        for requirement in config["requirements"]:
            requirement_code = requirement["requirement_id"]

            cur.execute(
                """
                SELECT id
                FROM tender_requirements
                WHERE tender_id = :tender_id
                  AND requirement_code = :requirement_code
                """,
                tender_id=tender_id,
                requirement_code=requirement_code,
            )

            row = cur.fetchone()

            if not row:
                raise RuntimeError(
                    f"Requirement missing from DB: "
                    f"{requirement_code}"
                )

            requirement_id = row[0]
            requirement_count += 1

            for order_no, evidence in enumerate(
                requirement.get("evidence", []),
                start=1,
            ):
                cur.execute(
                    """
                    INSERT INTO requirement_evidence_rules (
                        id,
                        requirement_id,
                        evidence_text,
                        evidence_order,
                        mandatory_evidence,
                        active
                    )
                    VALUES (
                        :id,
                        :requirement_id,
                        :evidence_text,
                        :evidence_order,
                        1,
                        1
                    )
                    """,
                    id=stable_uuid(
                        dataset_id,
                        "EVIDENCE",
                        requirement_code,
                        evidence,
                    ),
                    requirement_id=requirement_id,
                    evidence_text=evidence,
                    evidence_order=order_no,
                )

                evidence_count += 1

        conn.commit()

        print("==============================================")
        print(" DOCUMENT / EVIDENCE MASTER SEED COMPLETE")
        print("==============================================")
        print(f"Required documents:      {document_count}")
        print(f"Requirements processed: {requirement_count}")
        print(f"Evidence rules:          {evidence_count}")
        print()
        print("PASS: Document master committed to Oracle.")

    except Exception:
        conn.rollback()
        print("FAILED: transaction rolled back.")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
