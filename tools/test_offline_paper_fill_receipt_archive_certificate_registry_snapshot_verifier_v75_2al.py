import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from tools.offline_paper_fill_receipt_archive_certificate_registry_snapshot_verifier_v75_2al import *

SNAPSHOT_AT="2026-07-31T02:00:00+00:00"

def cfg():
    return {"verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY",
      "require_snapshot_integrity":True,"require_snapshot_manifest_integrity":True,
      "require_snapshot_index_integrity":True,"require_snapshot_checks_integrity":True,
      "require_snapshot_ledger_integrity":True,"require_deterministic_snapshot_id":True,
      "require_receipt_notional_recalculation":True,"require_zero_settlement_and_account_mutations":True,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"external_side_effects_allowed":False}

def src():
    rvid="FRV-AAAAAAAAAAAAAAAA"; source_hash="a"*64
    sid="FRS-"+hashlib.sha256(f"{rvid}|{source_hash}|{SNAPSHOT_AT}|75.2AK".encode()).hexdigest()[:16].upper()
    index=[{"snapshot_index":1,"registry_index":1,"certificate_index":1,"archive_index":1,
      "receipt_id":"FRC-AAAAAAAAAAAAAAAA","receipt_sha256":"b"*64,"fill_id":"FILL-AAAAAAAAAAAAAAAA",
      "symbol":"SPY","side":"BUY","filled_quantity":2,"fill_price":633.5,"notional_value":1267.0,
      "snapshot_state":"SNAPSHOTTED_VERIFIED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"}]
    manifest={"snapshot_id":sid,"registry_verification_id":rvid,"registry_id":"FCR-AAAAAAAAAAAAAAAA",
      "certificate_id":"FAC-AAAAAAAAAAAAAAAA","receipt_batch_id":"FRB-A","snapshotted_receipt_count":1,
      "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY",
      "snapshot_state":"SEALED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "snapshotted_at":SNAPSHOT_AT}
    checks=[{"check_index":i,"check":f"CHECK_{i}","state":"PASS" if i<9 else ("LOCKED" if i==9 else "ENFORCED")} for i in range(1,13)]
    ledger=[{"ledger_index":i,"event":f"EVENT_{i}","state":"PASS","snapshot_id":sid} for i in range(1,7)]
    s={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_created",
      "fill_receipt_archive_certificate_registry_snapshot_id":sid,
      "fill_receipt_archive_certificate_registry_verification_id":rvid,
      "fill_receipt_archive_certificate_registry_id":"FCR-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_verification_id":"FCV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_id":"FAC-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_verification_id":"FAV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_package_id":"FRA-AAAAAAAAAAAAAAAA",
      "fill_receipt_verification_id":"FILLV-AAAAAAAAAAAAAAAA","receipt_batch_id":"FRB-A",
      "snapshot_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
      "snapshot_state":"SEALED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "snapshotted_at":SNAPSHOT_AT,"snapshot_manifest":manifest,"snapshot_manifest_sha256":sha256_of(manifest),
      "snapshotted_receipt_count":1,"snapshot_index":index,"snapshot_index_sha256":sha256_of(index),
      "snapshot_checks":checks,"snapshot_checks_sha256":sha256_of(checks),
      "snapshot_ledger":ledger,"snapshot_ledger_sha256":sha256_of(ledger),
      "snapshot_gate":{"archive_certificate_registry_snapshot_created":True,"snapshot_immutable":True,
        "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY","settlement_execution_allowed":False,
        "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
        "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
        "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2AL"},
      "source_registry_verification_sha256":source_hash,"source_verified_registry_index_sha256":"c"*64,
      "source_verification_checks_sha256":"d"*64,"source_verification_ledger_sha256":"e"*64,
      "session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,"champion_candidate_id":"CAND-A",
      "settlements_created":0,"positions_updated":0,"cash_updates_created":0,"portfolio_updates_created":0,
      "external_orders_submitted":0,"broker_routes_created":0,"settlement_execution_allowed":False,
      "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
      "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
      "approved_for_live":False,"network_used":False,"safety_lock":{"lock_state":"ENFORCED"},
      "schema_version":"v75.2ak.offline_paper_fill_receipt_archive_certificate_registry_snapshot.1",
      "version":"75.2AK"}
    s["offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256"]=sha256_of(s)
    return s

class TestV752AL(unittest.TestCase):
    def build(self): return build_verification(src(),cfg())
    def rehash(self,s):
        s.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256",None)
        s["offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["verification_state"],"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT")
    def test_count(self): self.assertEqual(self.build()["verified_snapshotted_receipt_count"],1)
    def test_index_state(self): self.assertEqual(self.build()["verified_snapshot_index"][0]["verification_state"],"VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT")
    def test_hashes(self):
        o=self.build(); self.assertEqual(o["verified_snapshot_index_sha256"],sha256_of(o["verified_snapshot_index"]))
    def test_output_hash(self):
        o=self.build(); h=o.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256"); self.assertEqual(h,sha256_of(o))
    def test_deterministic_id(self): self.assertEqual(self.build()["fill_receipt_archive_certificate_registry_snapshot_verification_id"],self.build()["fill_receipt_archive_certificate_registry_snapshot_verification_id"])
    def test_no_mutations(self):
        o=self.build()
        for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created"): self.assertEqual(o[k],0)
    def test_no_live(self):
        o=self.build()
        for k in ("broker_routing_allowed","network_allowed","approved_for_live","network_used"): self.assertFalse(o[k])
    def test_source_not_mutated(self):
        s=src(); b=copy.deepcopy(s); build_verification(s,cfg()); self.assertEqual(s,b)
    def test_tampered_source(self):
        s=src(); s["cycle_id"]="BAD"; self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError,build_verification,s,cfg())
    def test_tampered_manifest(self):
        s=src(); s["snapshot_manifest"]["snapshot_effect"]="BAD"; s["snapshot_manifest_sha256"]=sha256_of(s["snapshot_manifest"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError,build_verification,s,cfg())
    def test_tampered_index(self):
        s=src(); s["snapshot_index"][0]["notional_value"]=1; s["snapshot_index_sha256"]=sha256_of(s["snapshot_index"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError,build_verification,s,cfg())
    def test_wrong_snapshot_id(self):
        s=src(); s["fill_receipt_archive_certificate_registry_snapshot_id"]="FRS-BAD"; s["snapshot_manifest"]["snapshot_id"]="FRS-BAD"
        for x in s["snapshot_ledger"]: x["snapshot_id"]="FRS-BAD"
        s["snapshot_manifest_sha256"]=sha256_of(s["snapshot_manifest"]); s["snapshot_ledger_sha256"]=sha256_of(s["snapshot_ledger"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError,build_verification,s,cfg())
    def test_settlement_rejected(self):
        s=src(); s["settlements_created"]=1; self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError,build_verification,s,cfg())
    def test_unsafe_config(self):
        c=cfg(); c["network_allowed"]=True
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError,build_verification,src(),c)
    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src()),encoding="utf-8"); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            rc=main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")])
            self.assertEqual(rc,0); self.assertTrue((p/"out/offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_v75_2al.json").exists())
    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            self.assertEqual(main(["--input",str(p/"missing.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
