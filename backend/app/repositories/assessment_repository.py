from __future__ import annotations

import json
from datetime import timezone
from uuid import uuid4

import oracledb

from app.db.oracle import acquire_connection
from app.schemas.assessment import AssessmentSummaryResponse, SubmissionResponse
from app.services.assessment.errors import AssessmentInputError, AssessmentNotFoundError


def rows(cursor):
    names = [item[0].lower() for item in cursor.description]
    return [dict(zip(names, [v.read() if hasattr(v, "read") else v for v in row]))
            for row in cursor.fetchall()]


TENDER_SQL = """
SELECT t.id tender_id, t.dataset_id, t.bid_number, t.title, b.name buyer,
       TO_CHAR(t.bid_end_at, 'YYYY-MM-DD"T"HH24:MI:SS.FF6TZH:TZM') closing_date,
       (SELECT COUNT(*) FROM bid_submissions s WHERE s.tender_id=t.id) submission_count
FROM tenders t LEFT JOIN buyers b ON b.id=t.buyer_id
"""
SUBMISSION_SQL = """
SELECT s.id submission_id, s.tender_id, s.bidder_id, b.legal_name bidder_name,
       b.pan_reference, t.dataset_id, t.bid_number, s.status, s.offered_model,
       s.mse_claimed,s.startup_claimed,s.nsic_claimed,s.emd_exemption_claimed,
       CASE WHEN r.id IS NULL THEN 0 ELSE 1 END assessment_available,
       r.compliance_score score, r.final_risk
FROM bid_submissions s JOIN bidders b ON b.id=s.bidder_id
JOIN tenders t ON t.id=s.tender_id
LEFT JOIN risk_assessments r ON r.submission_id=s.id
"""


class AssessmentRepository:
    def __init__(self, connection_factory=acquire_connection):
        self.connection_factory = connection_factory

    def query(self, sql, **binds):
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, binds)
                return rows(cursor)

    def tenders(self):
        return self.query(TENDER_SQL + " ORDER BY t.bid_number")

    def tender(self, tender_id):
        found = self.query(TENDER_SQL + " WHERE t.id=:id", id=tender_id)
        if not found:
            raise AssessmentNotFoundError("Tender not found")
        detail = found[0]
        detail["requirements"] = self.query(
            "SELECT requirement_code,title,description,weight,severity,applicability "
            "FROM tender_requirements WHERE tender_id=:id AND active=1 ORDER BY requirement_code", id=tender_id)
        detail["technical_requirements"] = self.query(
            "SELECT technical_code,parameter_name,minimum_requirement,classification "
            "FROM technical_requirements WHERE tender_id=:id ORDER BY technical_code", id=tender_id)
        detail["mandatory_documents"] = self.query(
            "SELECT document_code,document_name,mandatory,conditional,condition_text "
            "FROM tender_required_documents WHERE tender_id=:id AND active=1 ORDER BY document_code", id=tender_id)
        return detail

    def submission(self, submission_id):
        found = self.query(SUBMISSION_SQL + " WHERE s.id=:id", id=submission_id)
        if not found:
            raise AssessmentNotFoundError("Submission not found")
        return SubmissionResponse.model_validate(found[0])

    def submissions(self, tender_id):
        self.tender(tender_id)
        return self.query(SUBMISSION_SQL + " WHERE s.tender_id=:id ORDER BY b.legal_name", id=tender_id)

    def assessment(self, submission_id):
        # One query returns a consistent committed assessment snapshot, even during reassessment.
        found = self.query("""
            SELECT a.details_json, r.compliance_score, r.base_risk, r.final_risk,
                   SYS_EXTRACT_UTC(r.calculated_at) calculated_at
            FROM risk_assessments r JOIN audit_events a
              ON a.entity_id=r.id AND a.submission_id=r.submission_id
             AND a.event_type='ASSESSMENT_COMPLETED'
            WHERE r.submission_id=:id ORDER BY a.id DESC
            FETCH FIRST 1 ROW ONLY
        """, id=submission_id)
        if not found:
            raise AssessmentNotFoundError("Persisted assessment not found")
        row = found[0]
        snapshot = json.loads(row["details_json"])["assessment"]
        snapshot.update(score=row["compliance_score"], base_risk=row["base_risk"],
                        final_risk=row["final_risk"],
                        assessed_at=row["calculated_at"].replace(tzinfo=timezone.utc))
        return AssessmentSummaryResponse.model_validate(snapshot)

    def persist(self, summary: AssessmentSummaryResponse, verification):
        with self.connection_factory() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT tender_id,bidder_id FROM bid_submissions WHERE id=:id FOR UPDATE",
                                   id=summary.submission_id)
                    identity = cursor.fetchone()
                    if identity is None:
                        raise AssessmentNotFoundError("Submission not found")
                    if identity != (summary.tender_id, summary.bidder_id):
                        raise AssessmentInputError("Submission identity changed during assessment")
                    cursor.execute("SELECT requirement_code,id FROM tender_requirements WHERE tender_id=:id AND active=1",
                                   id=summary.tender_id)
                    requirements = dict(cursor.fetchall())
                    codes = [r.requirement_code for r in summary.requirement_results]
                    if len(codes) != 16 or len(set(codes)) != 16 or set(codes) != set(requirements):
                        raise AssessmentInputError("Assessment must contain exactly the configured 16 requirements")
                    cursor.execute("SELECT source_code,id FROM verification_sources WHERE active=1")
                    sources = dict(cursor.fetchall())
                    # These aliases reconcile the inspected registry codes with seeded source masters.
                    aliases = {"MOCK_DPIIT_REGISTRY": "MOCK_DPIIT_REGISTRY_IF_CLAIMED",
                               "MOCK_NSIC_REGISTRY": "MOCK_NSIC_REGISTRY_IF_CLAIMED",
                               "SYNTHETIC_EMD_PAYMENT_VERIFICATION": "SYNTHETIC_EMD_VERIFICATION"}
                    checks = []
                    for field in type(verification).model_fields:
                        source = getattr(verification, field)
                        if not hasattr(source, "source_system"):
                            continue
                        code = aliases.get(source.source_system, source.source_system)
                        if code not in sources:
                            raise AssessmentInputError("Verification source is not configured: " + code)
                        checks.append((sources[code], source))
                    cursor.execute("""DELETE FROM verification_checks WHERE submission_id=:id
                        AND JSON_VALUE(request_json,'$.generator')='BIDGUARD_ASSESSMENT'""", id=summary.submission_id)
                    cursor.execute("DELETE FROM requirement_results WHERE submission_id=:id", id=summary.submission_id)
                    cursor.execute("DELETE FROM risk_assessments WHERE submission_id=:id", id=summary.submission_id)
                    for source_id, source in checks:
                        cursor.setinputsizes(request_json=oracledb.DB_TYPE_CLOB, response_json=oracledb.DB_TYPE_CLOB,
                                             checked_at=oracledb.DB_TYPE_TIMESTAMP_TZ)
                        cursor.execute("""INSERT INTO verification_checks
                            (id,submission_id,verification_source_id,request_json,response_json,verification_status,checked_at)
                            VALUES (:id,:submission_id,:source_id,:request_json,:response_json,:state,:checked_at)""",
                            id=str(uuid4()), submission_id=summary.submission_id, source_id=source_id,
                            request_json=json.dumps({"generator": "BIDGUARD_ASSESSMENT", "source_code": source.source_system}),
                            response_json=source.model_dump_json(), state=source.verification_status,
                            checked_at=source.source_snapshot_at or verification.snapshot_at)
                    for result in summary.requirement_results:
                        cursor.setinputsizes(reason=oracledb.DB_TYPE_CLOB, metadata=oracledb.DB_TYPE_CLOB,
                                             evaluated_at=oracledb.DB_TYPE_TIMESTAMP_TZ)
                        cursor.execute("""INSERT INTO requirement_results
                            (id,submission_id,requirement_id,status,awarded_points,reason,ai_explanation,requires_human_review,evaluated_at)
                            VALUES (:id,:submission_id,:requirement_id,:status,:points,:reason,:metadata,:review,:evaluated_at)""",
                            id=str(uuid4()), submission_id=summary.submission_id,
                            requirement_id=requirements[result.requirement_code], status=result.status,
                            points=result.awarded_points, reason=result.reason, metadata=result.model_dump_json(),
                            review=int(result.requires_human_review), evaluated_at=summary.assessed_at)
                    assessment_id = str(uuid4())
                    cursor.setinputsizes(calculated_at=oracledb.DB_TYPE_TIMESTAMP_TZ)
                    cursor.execute("""INSERT INTO risk_assessments
                        (id,submission_id,compliance_score,base_risk,final_risk,calculated_at)
                        VALUES (:id,:submission_id,:score,:base,:final,:calculated_at)""",
                        id=assessment_id, submission_id=summary.submission_id, score=summary.score,
                        base=summary.base_risk, final=summary.final_risk, calculated_at=summary.assessed_at)
                    payload = {"assessment": summary.model_dump(mode="json"),
                               "requirement_count": len(codes),
                               "triggered_override_ids": [r.override_id for r in summary.triggered_risk_overrides],
                               "unknown_sources": verification.unknown_sources}
                    cursor.setinputsizes(details=oracledb.DB_TYPE_CLOB)
                    cursor.execute("""INSERT INTO audit_events
                        (tender_id,submission_id,actor_type,event_type,entity_type,entity_id,details_json)
                        VALUES (:tender_id,:submission_id,'SYSTEM','ASSESSMENT_COMPLETED','RISK_ASSESSMENT',:entity_id,:details)""",
                        tender_id=summary.tender_id, submission_id=summary.submission_id,
                        entity_id=assessment_id, details=json.dumps(payload, sort_keys=True, allow_nan=False))
                connection.commit()
            except Exception:
                connection.rollback()
                raise
