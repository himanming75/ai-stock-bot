import copy, json, tempfile, unittest
from pathlib import Path
from tools.registry_verifier_v75_2ar import *

def cfg():
    return {"verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_VERIFICATION_ONLY",
      "require_registry_integrity":True,"require_registry_manifest_integrity":True,
      "require_registered_index_integrity":True,"require_registry_checks_integrity":True,
      "require_registry_ledger_integrity":True,"require_deterministic_registry_id":True,
      "require_receipt_notional_recalculation":True,"require_zero_settlement_and_account_mutations":True,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,
      "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"broker_connection_allowed":False,"external_side_effects_allowed":False}

def src():
    registered_at="2026-07-31T00:00:00-07:00"
    vid="FCX-AAAAAAAAAAAAAAAA"
    source_sha="b"*64
    rid="FCRS-"+hashlib.sha256(f"{vid}|{source_sha}|{registered_at}|75.2AQ".encode()).hexdigest()[:16].upper()
    index=[{"registry_record_index":1,"certificate_record_index":1,"seal_index":1,"snapshot_index":1,
      "registry_index":1,"certificate_index":1,"archive_index":1,"receipt_id":"FRC-AAAAAAAAAAAAAAAA",
      "receipt_sha256":"a"*64,"fill_id":"FILL-AAAAAAAAAAAAAAAA","symbol":"SPY","side":"BUY",
      "filled_quantity":2,"fill_price":633.5,"notional_value":1267.0,
      "registry_state":"REGISTERED_VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"}]
    manifest={"registry_id":rid,"certificate_verification_id":vid,"certificate_id":"FSC-AAAAAAAAAAAAAAAA",
      "seal_id":"FSS-AAAAAAAAAAAAAAAA","snapshot_id":"FRS-AAAAAAAAAAAAAAAA","receipt_batch_id":"FRB-A",
      "registered_receipt_count":1,"registry_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRATION_ONLY",
      "registry_state":"REGISTERED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE",
      "registered_at":registered_at}
    checks=[{"check_index":i,"check":f"CHECK_{i}","state":"PASS"} for i in range(1,13)]
    ledger=[{"ledger_index":i,"event":f"EVENT_{i}","state":"PASS","registry_id":rid} for i in range(1,7)]
    s={"status":"PASS",
      "decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registered",
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id":rid,
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id":vid,
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id":"FSC-AAAAAAAAAAAAAAAA",
      "receipt_batch_id":"FRB-A",
      "registry_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_ONLY",
      "registry_state":"REGISTERED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE",
      "registered_at":registered_at,"registry_manifest":manifest,
      "registry_manifest_sha256":sha256_of(manifest),"registered_receipt_count":1,
      "registered_index":index,"registered_index_sha256":sha256_of(index),
      "registry_checks":checks,"registry_checks_sha256":sha256_of(checks),
      "registry_ledger":ledger,"registry_ledger_sha256":sha256_of(ledger),
      "registry_gate":{"archive_certificate_registry_snapshot_seal_certificate_registered":True,
        "registry_immutable":True,"registry_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRATION_ONLY",
        "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
        "portfolio_update_allowed":False,"external_order_submission_allowed":False,
        "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
        "network_allowed":False,"next_version":"75.2AR"},
      "source_certificate_verification_sha256":source_sha,
      "source_verified_certified_index_sha256":"c"*64,
      "source_verification_checks_sha256":"d"*64,"source_verification_ledger_sha256":"e"*64,
      "session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,
      "champion_candidate_id":"CAND-A","settlements_created":0,"positions_updated":0,
      "cash_updates_created":0,"portfolio_updates_created":0,"external_orders_submitted":0,
      "broker_routes_created":0,"settlement_execution_allowed":False,"position_update_allowed":False,
      "cash_update_allowed":False,"portfolio_update_allowed":False,
      "external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"approved_for_live":False,"network_used":False,
      "safety_lock":{"lock_state":"ENFORCED"},
      "schema_version":"v75.2aq.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry.1",
      "version":"75.2AQ"}
    s["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256"]=sha256_of(s)
    return s

class TestV752AR(unittest.TestCase):
    def build(self): return verify_registry(src(),cfg())
    def rehash(self,s):
        s.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256",None)
        s["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["verification_state"],"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY")
    def test_count(self): self.assertEqual(self.build()["verified_registered_receipt_count"],1)
    def test_deterministic_id(self): self.assertEqual(self.build()["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id"],self.build()["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id"])
    def test_hashes(self):
        o=self.build()
        self.assertEqual(o["verified_registered_index_sha256"],sha256_of(o["verified_registered_index"]))
        self.assertEqual(o["verification_checks_sha256"],sha256_of(o["verification_checks"]))
        self.assertEqual(o["verification_ledger_sha256"],sha256_of(o["verification_ledger"]))
    def test_output_hash(self):
        o=self.build(); h=o.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256")
        self.assertEqual(h,sha256_of(o))
    def test_index_state(self): self.assertTrue(self.build()["verified_registered_index"][0]["verification_state"].startswith("VERIFIED_"))
    def test_no_live(self):
        o=self.build()
        for k in ("network_allowed","broker_routing_allowed","approved_for_live","network_used"): self.assertFalse(o[k])
    def test_no_mutations(self):
        o=self.build()
        for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created"): self.assertEqual(o[k],0)
    def test_source_not_mutated(self):
        s=src(); original=copy.deepcopy(s); verify_registry(s,cfg()); self.assertEqual(s,original)
    def test_tampered_source(self):
        s=src(); s["cycle_id"]="BAD"
        self.assertRaises(RegistryVerificationError,verify_registry,s,cfg())
    def test_tampered_index(self):
        s=src(); s["registered_index"][0]["notional_value"]=1
        s["registered_index_sha256"]=sha256_of(s["registered_index"]); self.rehash(s)
        self.assertRaises(RegistryVerificationError,verify_registry,s,cfg())
    def test_tampered_manifest(self):
        s=src(); s["registry_manifest"]["registered_receipt_count"]=2
        s["registry_manifest_sha256"]=sha256_of(s["registry_manifest"]); self.rehash(s)
        self.assertRaises(RegistryVerificationError,verify_registry,s,cfg())
    def test_wrong_registry_id(self):
        s=src(); s["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id"]="FCRS-BAD"
        self.rehash(s); self.assertRaises(RegistryVerificationError,verify_registry,s,cfg())
    def test_settlement_rejected(self):
        s=src(); s["settlements_created"]=1; self.rehash(s)
        self.assertRaises(RegistryVerificationError,verify_registry,s,cfg())
    def test_unsafe_config(self):
        c=cfg(); c["network_allowed"]=True
        self.assertRaises(RegistryVerificationError,verify_registry,src(),c)
    def test_checks_ledger(self):
        o=self.build(); self.assertEqual(len(o["verification_checks"]),12); self.assertEqual(len(o["verification_ledger"]),6)
    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src()),encoding="utf-8")
            (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),0)
            self.assertTrue((p/"out/offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_v75_2ar.json").exists())
    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            self.assertEqual(main(["--input",str(p/"missing.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__":
    unittest.main()
