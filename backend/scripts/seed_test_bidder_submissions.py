from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.oracle import acquire_connection, initialize_pool, close_pool
from app.services.assessment.prototype_evidence import read_json


def ensure_prototype_submissions(settings):
    root = settings.prototype_dataset_root
    config = read_json(root / "config/tender_requirements.json")
    identities = []
    with acquire_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM tenders WHERE dataset_id=:dataset AND bid_number=:bid FOR UPDATE",
                               dataset=config["dataset_id"], bid=config["tender"]["bid_number"])
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("Seed the prototype tender before bidder metadata")
                tender_id = row[0]
                for directory in sorted((root / "bidders").iterdir()):
                    if not (directory / "bidder_profile.json").is_file():
                        continue
                    profile = read_json(directory / "bidder_profile.json")
                    manifest = read_json(directory / "document_manifest.json")
                    identity, claims = profile["bidder_identity"], profile["claims"]
                    if identity["bidder_id"] not in {"BIDDER_A", "BIDDER_B", "BIDDER_C"}:
                        continue
                    if manifest["bidder_id"] != identity["bidder_id"] or profile["dataset_id"] != config["dataset_id"]:
                        raise ValueError("Prototype metadata identity mismatch")
                    cursor.execute("SELECT id FROM bidders WHERE pan_reference=:pan AND legal_name=:name",
                                   pan=identity["pan"], name=identity["legal_name"])
                    existing = cursor.fetchall()
                    if len(existing) > 1:
                        raise ValueError("Ambiguous existing bidder identity")
                    bidder_id = existing[0][0] if existing else str(uuid5(NAMESPACE_URL, "::".join((config["dataset_id"], identity["bidder_id"]))))
                    if not existing:
                        cursor.execute("""INSERT INTO bidders (id,legal_name,entity_type,registered_address,
                            pan_reference,gst_reference,udyam_reference,is_synthetic)
                            VALUES (:id,:name,:entity,:address,:pan,:gst,:udyam,1)""",
                            id=bidder_id, name=identity["legal_name"], entity=identity["entity_type"],
                            address=identity["registered_address"], pan=identity["pan"], gst=identity["gstin"], udyam=identity["udyam"])
                    cursor.execute("SELECT id FROM bid_submissions WHERE tender_id=:tender AND bidder_id=:bidder",
                                   tender=tender_id, bidder=bidder_id)
                    existing_submission = cursor.fetchone()
                    submission_id = existing_submission[0] if existing_submission else str(uuid5(NAMESPACE_URL, "::".join((tender_id, bidder_id, "submission"))))
                    if not existing_submission:
                        cursor.execute("""INSERT INTO bid_submissions
                            (id,tender_id,bidder_id,status,mse_claimed,startup_claimed,nsic_claimed,
                             emd_exemption_claimed,offered_make,offered_model)
                            VALUES (:id,:tender,:bidder,'UPLOADED',:mse,:startup,:nsic,:emd,:make,:model)""",
                            id=submission_id, tender=tender_id, bidder=bidder_id,
                            mse=int(claims["mse_purchase_preference"]), startup=int(claims["startup_turnover_relaxation"]),
                            nsic=int(claims.get("nsic_related_benefit", bool(identity.get("nsic_spr")))),
                            emd=int(claims["emd_exemption"]), make=profile["offered_product"]["brand"], model=profile["offered_product"]["model"])
                    identities.append((identity["bidder_id"], submission_id, tender_id))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return identities


if __name__ == "__main__":
    settings = get_settings()
    initialize_pool(settings)
    try:
        for row in ensure_prototype_submissions(settings):
            print(*row)
    finally:
        close_pool()
