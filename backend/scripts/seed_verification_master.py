from __future__ import annotations

import json
import uuid
from pathlib import Path

import oracledb

from script_config import DATA_ROOT, oracle_connection_kwargs

TENDER_JSON = DATA_ROOT / "config" / "tender_requirements.json"
SCORING_JSON = DATA_ROOT / "config" / "scoring_rules.json"


def stable_uuid(*parts: str) -> str:
    value = "::".join(str(p) for p in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    tender_config = load_json(TENDER_JSON)
    scoring_config = load_json(SCORING_JSON)

    dataset_id = tender_config["dataset_id"]

    conn = oracledb.connect(**oracle_connection_kwargs())

    try:
        cur = conn.cursor()

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
            raise RuntimeError("Tender is not seeded yet.")

        tender_id = row[0]

        # -----------------------------
        # clear only master config
        # -----------------------------
        cur.execute(
            """
            DELETE FROM scoring_profiles
            WHERE tender_id = :tender_id
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

        # -----------------------------
        # scoring profile
        # -----------------------------
        profile_id = stable_uuid(dataset_id, "SCORING_PROFILE")

        cur.execute(
            """
            INSERT INTO scoring_profiles (
                id,
                tender_id,
                profile_code,
                profile_name,
                total_weight,
                active
            )
            VALUES (
                :id,
                :tender_id,
                :profile_code,
                :profile_name,
                :total_weight,
                1
            )
            """,
            id=profile_id,
            tender_id=tender_id,
            profile_code="DEFAULT",
            profile_name="SIH26100 Tender Compliance Scoring",
            total_weight=100,
        )

        # -----------------------------
        # status credits
        # -----------------------------
        credits = scoring_config["status_credit"]

        credit_map = {
            "COMPLIANT": credits["COMPLIANT"],
            "NEEDS_REVIEW": credits["NEEDS_REVIEW"],
            "NON_COMPLIANT": credits["NON_COMPLIANT"],
            "MISSING": credits["MISSING"],
        }

        for status_code, factor in credit_map.items():
            cur.execute(
                """
                INSERT INTO scoring_status_credits (
                    id,
                    scoring_profile_id,
                    status_code,
                    credit_factor,
                    exclude_from_total
                )
                VALUES (
                    :id,
                    :profile_id,
                    :status_code,
                    :factor,
                    0
                )
                """,
                id=stable_uuid(
                    dataset_id,
                    "STATUS_CREDIT",
                    status_code,
                ),
                profile_id=profile_id,
                status_code=status_code,
                factor=factor,
            )

        # N/A is excluded and normalized
        cur.execute(
            """
            INSERT INTO scoring_status_credits (
                id,
                scoring_profile_id,
                status_code,
                credit_factor,
                exclude_from_total
            )
            VALUES (
                :id,
                :profile_id,
                'NOT_APPLICABLE',
                0,
                1
            )
            """,
            id=stable_uuid(
                dataset_id,
                "STATUS_CREDIT",
                "NOT_APPLICABLE",
            ),
            profile_id=profile_id,
        )

        # -----------------------------
        # risk bands
        # -----------------------------
        risk_bands = [
            ("LOW", 90, 100, 1, 1, 1),
            ("MEDIUM", 75, 90, 1, 0, 2),
            ("HIGH", 50, 75, 1, 0, 3),
            ("CRITICAL", 0, 50, 1, 0, 4),
        ]

        for (
            risk_level,
            min_score,
            max_score,
            min_inc,
            max_inc,
            display_order,
        ) in risk_bands:
            cur.execute(
                """
                INSERT INTO risk_bands (
                    id,
                    scoring_profile_id,
                    risk_level,
                    min_score,
                    max_score,
                    min_inclusive,
                    max_inclusive,
                    display_order
                )
                VALUES (
                    :id,
                    :profile_id,
                    :risk_level,
                    :min_score,
                    :max_score,
                    :min_inc,
                    :max_inc,
                    :display_order
                )
                """,
                id=stable_uuid(
                    dataset_id,
                    "RISK_BAND",
                    risk_level,
                ),
                profile_id=profile_id,
                risk_level=risk_level,
                min_score=min_score,
                max_score=max_score,
                min_inc=min_inc,
                max_inc=max_inc,
                display_order=display_order,
            )

        # -----------------------------
        # risk overrides
        # -----------------------------
        overrides = scoring_config["risk_overrides"]

        for override in overrides:
            cur.execute(
                """
                INSERT INTO risk_override_rules (
                    id,
                    scoring_profile_id,
                    override_code,
                    description,
                    minimum_risk_level,
                    trigger_json,
                    active
                )
                VALUES (
                    :id,
                    :profile_id,
                    :override_code,
                    :description,
                    :minimum_risk,
                    :trigger_json,
                    1
                )
                """,
                id=stable_uuid(
                    dataset_id,
                    "RISK_OVERRIDE",
                    override["override_id"],
                ),
                profile_id=profile_id,
                override_code=override["override_id"],
                description=override["condition"],
                minimum_risk=override["minimum_risk"],
                trigger_json=json.dumps(
                    {
                        "condition": override["condition"]
                    },
                    ensure_ascii=False,
                ),
            )

        # -----------------------------
        # required documents
        # -----------------------------
        required_documents = {}

        for req in tender_config["requirements"]:
            for doc in req.get("required_documents", []):
                if isinstance(doc, str):
                    code = doc
                    name = doc.replace("_", " ").title()
                    mandatory = 1
                    conditional = 0
                    condition_text = None
                else:
                    code = doc["document_code"]
                    name = doc.get(
                        "document_name",
                        code.replace("_", " ").title(),
                    )
                    mandatory = int(
                        doc.get("mandatory", True)
                    )
                    conditional = int(
                        doc.get("conditional", False)
                    )
                    condition_text = doc.get("condition")

                required_documents[code] = {
                    "name": name,
                    "mandatory": mandatory,
                    "conditional": conditional,
                    "condition_text": condition_text,
                }

        required_document_ids = {}

        for code, cfg in required_documents.items():
            doc_id = stable_uuid(
                dataset_id,
                "REQUIRED_DOCUMENT",
                code,
            )
            required_document_ids[code] = doc_id

            cur.execute(
                """
                INSERT INTO tender_required_documents (
                    id,
                    tender_id,
                    document_code,
                    document_name,
                    mandatory,
                    conditional,
                    condition_text,
                    active
                )
                VALUES (
                    :id,
                    :tender_id,
                    :code,
                    :name,
                    :mandatory,
                    :conditional,
                    :condition_text,
                    1
                )
                """,
                id=doc_id,
                tender_id=tender_id,
                code=code,
                name=cfg["name"],
                mandatory=cfg["mandatory"],
                conditional=cfg["conditional"],
                condition_text=cfg["condition_text"],
            )

        # -----------------------------
        # requirement mappings
        # -----------------------------
        req_count = 0
        doc_map_count = 0
        source_map_count = 0

        for req in tender_config["requirements"]:
            cur.execute(
                """
                SELECT id
                FROM tender_requirements
                WHERE tender_id = :tender_id
                  AND requirement_code = :code
                """,
                tender_id=tender_id,
                code=req["requirement_id"],
            )
            req_row = cur.fetchone()

            if not req_row:
                raise RuntimeError(
                    f"Requirement missing in DB: "
                    f"{req['requirement_id']}"
                )

            requirement_id = req_row[0]
            req_count += 1

            # requirement -> document
            for doc in req.get("required_documents", []):
                code = (
                    doc
                    if isinstance(doc, str)
                    else doc["document_code"]
                )

                doc_id = required_document_ids[code]

                cur.execute(
                    """
                    INSERT INTO requirement_document_rules (
                        id,
                        requirement_id,
                        required_document_id,
                        evidence_role,
                        mandatory_evidence
                    )
                    VALUES (
                        :id,
                        :requirement_id,
                        :document_id,
                        'PRIMARY_EVIDENCE',
                        1
                    )
                    """,
                    id=stable_uuid(
                        dataset_id,
                        "REQ_DOC",
                        req["requirement_id"],
                        code,
                    ),
                    requirement_id=requirement_id,
                    document_id=doc_id,
                )

                doc_map_count += 1

            # requirement -> verification source
            for priority, source_code in enumerate(
                req.get("authoritative_sources", []),
                start=1,
            ):
                cur.execute(
                    """
                    SELECT id
                    FROM verification_sources
                    WHERE source_code = :source_code
                    """,
                    source_code=source_code,
                )

                source_row = cur.fetchone()

                if not source_row:
                    raise RuntimeError(
                        f"Verification source missing: "
                        f"{source_code}"
                    )

                source_id = source_row[0]

                cur.execute(
                    """
                    INSERT INTO requirement_verification_sources (
                        id,
                        requirement_id,
                        verification_source_id,
                        priority_order,
                        authoritative
                    )
                    VALUES (
                        :id,
                        :requirement_id,
                        :source_id,
                        :priority_order,
                        1
                    )
                    """,
                    id=stable_uuid(
                        dataset_id,
                        "REQ_SOURCE",
                        req["requirement_id"],
                        source_code,
                    ),
                    requirement_id=requirement_id,
                    source_id=source_id,
                    priority_order=priority,
                )

                source_map_count += 1

        conn.commit()

        print("============================================")
        print(" VERIFICATION MASTER SEED COMPLETE")
        print("============================================")
        print("Scoring profiles:              1")
        print("Status credits:                5")
        print("Risk bands:                    4")
        print(f"Risk overrides:                {len(overrides)}")
        print(
            f"Required document definitions: {len(required_documents)}"
        )
        print(f"Requirements mapped:           {req_count}")
        print(f"Requirement-document mappings: {doc_map_count}")
        print(f"Requirement-source mappings:   {source_map_count}")
        print()
        print("PASS: Verification master committed.")

    except Exception:
        conn.rollback()
        print("FAILED: transaction rolled back.")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
