import copy, json, tempfile, unittest
from pathlib import Path
from tools.offline_paper_fill_receipt_archive_certificate_registry_snapshot_builder_v75_2ak import *

SNAPSHOT_AT="2026-07-31T02:00:00+00:00"

def cfg():
    return {"snapshot_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
      "require_registry_verification_integrity":True,"require_verified_registry_index_integrity":True,
      "require_verification_checks_integrity":True,"require_verification_ledger_integrity":True,
      "require_zero_settlement_and_account_mutations":True,"create_snapshot_manifest":True,
      "create_snapshot_index":True,"create_snapshot_checks":True,"create_snapshot_ledger":True,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"external_side_effects_allowed":False}

def src():
    index=[{"registry_index":1,"certificate_index":1,"archive_index":1,"receipt_id":"FRC-AAAAAAAAAAAAAAAA",
      "receipt_sha256":"a"*64,"fill_id":"FILL-AAAAAAAAAAAAAAAA","symbol":"SPY","side":"BUY",
      "filled_quantity":2,"fill_price":633.5,"notional_value":1267.0,
      "verification_state":"VERIFIED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"}]
    checks=[{"check_index":i,"check":f"CHECK_{i}","state":"PASS" if i<9 else ("LOCKED" if i==9 else "ENFORCED")} for i in range(1,13)]
    ledger=[{"ledger_index":i,"event":f"EVENT_{i}","state":"PASS","registry_verification_id":"FRV-AAAAAAAAAAAAAAAA"} for i in range(1,7)]
    s={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_registry_verified",
      "fill_receipt_archive_certificate_registry_verification_id":"FRV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_registry_id":"FCR-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_verification_id":"FCV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_id":"FAC-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_verification_id":"FAV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_package_id":"FRA-AAAAAAAAAAAAAAAA",
      "fill_receipt_verification_id":"FILLV-AAAAAAAAAAAAAAAA","receipt_batch_id":"FRB-A",
      "verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_VERIFICATION_ONLY",
      "verification_state":"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY",
      "archive_certificate_registry_verified":True,"verified_registered_receipt_count":1,
      "verified_registry_index":index,"verified_registry_index_sha256":sha256_of(index),
      "verification_checks":checks,"verification_checks_sha256":sha256_of(checks),
      "verification_ledger":ledger,"verification_ledger_sha256":sha256_of(ledger),
      "verification_gate":{"archive_certificate_registry_verified":True,"registry_immutable":True,
        "registry_effect":"OFFLINE_INFORMATIONAL_REGISTRATION_ONLY","settlement_execution_allowed":False,
        "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
        "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
        "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2AK"},
      "source_registry_sha256":"b"*64,"source_registry_entry_sha256":"c"*64,
      "source_registry_index_sha256":"d"*64,"source_registry_checks_sha256":"e"*64,
      "source_registry_ledger_sha256":"f"*64,"session_id":"PAPER-A","cycle_id":"PCS-A",
      "cycle_sequence":1,"champion_candidate_id":"CAND-A","settlements_created":0,"positions_updated":0,
      "cash_updates_created":0,"portfolio_updates_created":0,"external_orders_submitted":0,
      "broker_routes_created":0,"settlement_execution_allowed":False,"position_update_allowed":False,
      "cash_update_allowed":False,"portfolio_update_allowed":False,"external_order_submission_allowed":False,
      "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"broker_connection_allowed":False,"approved_for_live":False,
      "network_used":False,"safety_lock":{"lock_state":"ENFORCED"},
      "schema_version":"v75.2aj.offline_paper_fill_receipt_archive_certificate_registry_verification.1",
      "version":"75.2AJ"}
    s["offline_paper_fill_receipt_archive_certificate_registry_verification_sha256"]=sha256_of(s)
    return s

class TestV752AK(unittest.TestCase):
    def build(self): return build_snapshot(src(),cfg(),SNAPSHOT_AT)
    def rehash(self,s):
        s.pop("offline_paper_fill_receipt_archive_certificate_registry_verification_sha256",None)
        s["offline_paper_fill_receipt_archive_certificate_registry_verification_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["snapshot_state"],"SEALED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT")
    def test_count(self): self.assertEqual(self.build()["snapshotted_receipt_count"],1)
    def test_manifest(self): self.assertEqual(self.build()["snapshot_manifest"]["snapshot_effect"],"OFFLINE_IMMUTABLE_EVIDENCE_ONLY")
    def test_index_state(self): self.assertEqual(self.build()["snapshot_index"][0]["snapshot_state"],"SNAPSHOTTED_VERIFIED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT")
    def test_hashes(self):
        o=self.build(); self.assertEqual(o["snapshot_manifest_sha256"],sha256_of(o["snapshot_manifest"])); self.assertEqual(o["snapshot_index_sha256"],sha256_of(o["snapshot_index"]))
    def test_output_hash(self):
        o=self.build(); h=o.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256"); self.assertEqual(h,sha256_of(o))
    def test_deterministic_id(self): self.assertEqual(self.build()["fill_receipt_archive_certificate_registry_snapshot_id"],self.build()["fill_receipt_archive_certificate_registry_snapshot_id"])
    def test_no_mutations(self):
        o=self.build()
        for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created"): self.assertEqual(o[k],0)
    def test_no_live(self):
        o=self.build()
        for k in ("broker_routing_allowed","network_allowed","approved_for_live","network_used"): self.assertFalse(o[k])
    def test_source_not_mutated(self):
        s=src(); b=copy.deepcopy(s); build_snapshot(s,cfg(),SNAPSHOT_AT); self.assertEqual(s,b)
    def test_tampered_source(self):
        s=src(); s["cycle_id"]="BAD"; self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError,build_snapshot,s,cfg(),SNAPSHOT_AT)
    def test_tampered_index(self):
        s=src(); s["verified_registry_index"][0]["notional_value"]=1; s["verified_registry_index_sha256"]=sha256_of(s["verified_registry_index"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError,build_snapshot,s,cfg(),SNAPSHOT_AT)
    def test_settlement_rejected(self):
        s=src(); s["settlements_created"]=1; self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError,build_snapshot,s,cfg(),SNAPSHOT_AT)
    def test_unsafe_config(self):
        c=cfg(); c["network_allowed"]=True
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError,build_snapshot,src(),c,SNAPSHOT_AT)
    def test_checks_ledger(self):
        o=self.build(); self.assertEqual(len(o["snapshot_checks"]),12); self.assertEqual(len(o["snapshot_ledger"]),6)
    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src()),encoding="utf-8"); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            rc=main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--snapshotted-at",SNAPSHOT_AT])
            self.assertEqual(rc,0); self.assertTrue((p/"out/offline_paper_fill_receipt_archive_certificate_registry_snapshot_v75_2ak.json").exists())
    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            self.assertEqual(main(["--input",str(p/"missing.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
