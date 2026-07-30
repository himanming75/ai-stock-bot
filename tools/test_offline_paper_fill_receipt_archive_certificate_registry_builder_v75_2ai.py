import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from tools.offline_paper_fill_receipt_archive_certificate_registry_builder_v75_2ai import *

REGISTERED_AT="2026-07-31T01:00:00+00:00"

def cfg():
    return {"registry_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_ONLY",
    "require_certificate_verification_integrity":True,"require_verified_certified_receipts_integrity":True,
    "require_verification_checks_integrity":True,"require_verification_ledger_integrity":True,
    "require_zero_settlement_and_account_mutations":True,"create_registry_entry":True,"create_registry_index":True,
    "create_registry_checks":True,"create_registry_ledger":True,
    "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
    "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
    "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,
    "broker_connection_allowed":False,"external_side_effects_allowed":False}

def src():
    vid="FCV-AAAAAAAAAAAAAAAA"
    receipts=[{"certificate_index":1,"archive_index":1,"receipt_id":"FRC-AAAAAAAAAAAAAAAA","receipt_sha256":"a"*64,
    "fill_id":"FILL-AAAAAAAAAAAAAAAA","symbol":"SPY","side":"BUY","filled_quantity":2,"fill_price":633.5,
    "notional_value":1267.0,"verification_state":"VERIFIED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"}]
    checks=[{"check_index":i,"check":f"CHECK_{i}","state":"PASS" if i<9 else ("LOCKED" if i==9 else "ENFORCED")} for i in range(1,13)]
    ledger=[{"ledger_index":i,"event":f"EVENT_{i}","state":"PASS","certificate_verification_id":vid} for i in range(1,7)]
    s={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_verified",
    "fill_receipt_archive_certificate_verification_id":vid,"fill_receipt_archive_certificate_id":"FAC-AAAAAAAAAAAAAAAA",
    "fill_receipt_archive_verification_id":"FAV-AAAAAAAAAAAAAAAA","fill_receipt_archive_package_id":"FRA-AAAAAAAAAAAAAAAA",
    "fill_receipt_verification_id":"FRV-AAAAAAAAAAAAAAAA","receipt_batch_id":"FRB-A",
    "verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_VERIFICATION_ONLY",
    "verification_state":"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE","archive_certificate_verified":True,
    "verified_certified_receipt_count":1,"verified_certified_receipts":receipts,"verified_certified_receipts_sha256":sha256_of(receipts),
    "verification_checks":checks,"verification_checks_sha256":sha256_of(checks),
    "verification_ledger":ledger,"verification_ledger_sha256":sha256_of(ledger),
    "verification_gate":{"archive_certificate_verified":True,"archive_certificate_immutable":True,
    "certificate_effect":"INFORMATIONAL_ARCHIVE_ATTESTATION_ONLY","settlement_execution_allowed":False,
    "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
    "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
    "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2AI"},
    "source_archive_certificate_sha256":"b"*64,"source_certificate_summary_sha256":"c"*64,
    "source_certified_receipts_sha256":"d"*64,"source_certificate_checks_sha256":"e"*64,
    "source_certificate_ledger_sha256":"f"*64,"session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,
    "champion_candidate_id":"CAND-A","settlements_created":0,"positions_updated":0,"cash_updates_created":0,
    "portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
    "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
    "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
    "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,
    "broker_connection_allowed":False,"approved_for_live":False,"network_used":False,
    "safety_lock":{"lock_state":"ENFORCED"},"schema_version":"v75.2ah.offline_paper_fill_receipt_archive_certificate_verification.1","version":"75.2AH"}
    s["offline_paper_fill_receipt_archive_certificate_verification_sha256"]=sha256_of(s); return s

class TestV752AI(unittest.TestCase):
    def build(self): return build_registry(src(),cfg(),REGISTERED_AT)
    def rehash(self,s):
        s.pop("offline_paper_fill_receipt_archive_certificate_verification_sha256",None)
        s["offline_paper_fill_receipt_archive_certificate_verification_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_registry_state(self): self.assertEqual(self.build()["registry_state"],"REGISTERED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE")
    def test_entry(self): self.assertEqual(self.build()["registry_entry"]["registry_effect"],"OFFLINE_INFORMATIONAL_REGISTRATION_ONLY")
    def test_count(self): self.assertEqual(self.build()["registered_receipt_count"],1)
    def test_index_state(self): self.assertEqual(self.build()["registry_index"][0]["registry_state"],"REGISTERED_VERIFIED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT")
    def test_hashes(self):
        o=self.build(); self.assertEqual(o["registry_entry_sha256"],sha256_of(o["registry_entry"])); self.assertEqual(o["registry_index_sha256"],sha256_of(o["registry_index"]))
    def test_output_hash(self):
        o=self.build(); h=o.pop("offline_paper_fill_receipt_archive_certificate_registry_sha256"); self.assertEqual(h,sha256_of(o))
    def test_deterministic_id(self): self.assertEqual(self.build()["fill_receipt_archive_certificate_registry_id"],self.build()["fill_receipt_archive_certificate_registry_id"])
    def test_no_mutations(self):
        o=self.build()
        for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created"): self.assertEqual(o[k],0)
    def test_no_live(self):
        o=self.build()
        for k in ("broker_routing_allowed","network_allowed","approved_for_live","network_used"): self.assertFalse(o[k])
    def test_source_not_mutated(self):
        s=src(); b=copy.deepcopy(s); build_registry(s,cfg(),REGISTERED_AT); self.assertEqual(s,b)
    def test_tampered_source(self):
        s=src(); s["cycle_id"]="BAD"; self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistryError,build_registry,s,cfg(),REGISTERED_AT)
    def test_tampered_receipt(self):
        s=src(); s["verified_certified_receipts"][0]["notional_value"]=1; s["verified_certified_receipts_sha256"]=sha256_of(s["verified_certified_receipts"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistryError,build_registry,s,cfg(),REGISTERED_AT)
    def test_settlement_rejected(self):
        s=src(); s["settlements_created"]=1; self.rehash(s); self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistryError,build_registry,s,cfg(),REGISTERED_AT)
    def test_unsafe_config(self):
        c=cfg(); c["network_allowed"]=True; self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistryError,build_registry,src(),c,REGISTERED_AT)
    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src()),encoding="utf-8"); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            rc=main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--registered-at",REGISTERED_AT])
            self.assertEqual(rc,0); self.assertTrue((p/"out/offline_paper_fill_receipt_archive_certificate_registry_v75_2ai.json").exists())
    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            self.assertEqual(main(["--input",str(p/"missing.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)
    def test_registry_checks_ledger(self):
        o=self.build(); self.assertEqual(len(o["registry_checks"]),12); self.assertEqual(len(o["registry_ledger"]),6)

if __name__=="__main__": unittest.main()
