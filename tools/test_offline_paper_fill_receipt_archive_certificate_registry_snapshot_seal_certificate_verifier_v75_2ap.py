import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from tools.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verifier_v75_2ap import *

CERTIFIED_AT="2026-07-31T04:00:00+00:00"

def cfg():
    return {"verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_VERIFICATION_ONLY",
      "require_certificate_integrity":True,"require_certificate_manifest_integrity":True,
      "require_certified_index_integrity":True,"require_certificate_checks_integrity":True,
      "require_certificate_ledger_integrity":True,"require_deterministic_certificate_id":True,
      "require_receipt_notional_recalculation":True,"require_zero_settlement_and_account_mutations":True,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"external_side_effects_allowed":False}

def src():
    svid="FSX-AAAAAAAAAAAAAAAA"; source_hash="a"*64
    cid="FSC-"+hashlib.sha256(f"{svid}|{source_hash}|{CERTIFIED_AT}|75.2AO".encode()).hexdigest()[:16].upper()
    index=[{"certificate_record_index":1,"seal_index":1,"snapshot_index":1,"registry_index":1,
      "certificate_index":1,"archive_index":1,"receipt_id":"FRC-AAAAAAAAAAAAAAAA","receipt_sha256":"b"*64,
      "fill_id":"FILL-AAAAAAAAAAAAAAAA","symbol":"SPY","side":"BUY","filled_quantity":2,
      "fill_price":633.5,"notional_value":1267.0,
      "certificate_state":"CERTIFIED_VERIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"}]
    manifest={"certificate_id":cid,"seal_verification_id":svid,"seal_id":"FSS-AAAAAAAAAAAAAAAA",
      "snapshot_id":"FRS-AAAAAAAAAAAAAAAA","registry_id":"FCR-AAAAAAAAAAAAAAAA",
      "receipt_batch_id":"FRB-A","certified_receipt_count":1,
      "certificate_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_ONLY",
      "certificate_state":"CERTIFIED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL",
      "certified_at":CERTIFIED_AT}
    checks=[{"check_index":i,"check":f"CHECK_{i}","state":"PASS" if i<9 else ("LOCKED" if i==9 else "ENFORCED")} for i in range(1,13)]
    ledger=[{"ledger_index":i,"event":f"EVENT_{i}","state":"PASS","certificate_id":cid} for i in range(1,7)]
    s={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_created",
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id":cid,
      "fill_receipt_archive_certificate_registry_snapshot_seal_verification_id":svid,
      "fill_receipt_archive_certificate_registry_snapshot_seal_id":"FSS-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_registry_snapshot_verification_id":"FSV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_registry_snapshot_id":"FRS-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_registry_verification_id":"FRV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_registry_id":"FCR-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_verification_id":"FCV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_certificate_id":"FAC-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_verification_id":"FAV-AAAAAAAAAAAAAAAA",
      "fill_receipt_archive_package_id":"FRA-AAAAAAAAAAAAAAAA",
      "fill_receipt_verification_id":"FILLV-AAAAAAAAAAAAAAAA","receipt_batch_id":"FRB-A",
      "certificate_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_ONLY",
      "certificate_state":"CERTIFIED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL",
      "certified_at":CERTIFIED_AT,"certificate_manifest":manifest,"certificate_manifest_sha256":sha256_of(manifest),
      "certified_receipt_count":1,"certified_index":index,"certified_index_sha256":sha256_of(index),
      "certificate_checks":checks,"certificate_checks_sha256":sha256_of(checks),
      "certificate_ledger":ledger,"certificate_ledger_sha256":sha256_of(ledger),
      "certificate_gate":{"archive_certificate_registry_snapshot_seal_certificate_created":True,
        "certificate_immutable":True,"certificate_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_ONLY",
        "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
        "portfolio_update_allowed":False,"external_order_submission_allowed":False,
        "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
        "network_allowed":False,"next_version":"75.2AP"},
      "source_seal_verification_sha256":source_hash,"source_verified_sealed_index_sha256":"c"*64,
      "source_verification_checks_sha256":"d"*64,"source_verification_ledger_sha256":"e"*64,
      "session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,"champion_candidate_id":"CAND-A",
      "settlements_created":0,"positions_updated":0,"cash_updates_created":0,"portfolio_updates_created":0,
      "external_orders_submitted":0,"broker_routes_created":0,"settlement_execution_allowed":False,
      "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
      "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
      "approved_for_live":False,"network_used":False,"safety_lock":{"lock_state":"ENFORCED"},
      "schema_version":"v75.2ao.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate.1",
      "version":"75.2AO"}
    s["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_sha256"]=sha256_of(s)
    return s

class TestV752AP(unittest.TestCase):
    def build(self): return build_verification(src(),cfg())
    def rehash(self,s):
        s.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_sha256",None)
        s["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["verification_state"],"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE")
    def test_count(self): self.assertEqual(self.build()["verified_certified_receipt_count"],1)
    def test_index_state(self): self.assertEqual(self.build()["verified_certified_index"][0]["verification_state"],"VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT")
    def test_hashes(self): self.assertEqual(self.build()["verified_certified_index_sha256"],sha256_of(self.build()["verified_certified_index"]))
    def test_output_hash(self):
        o=self.build(); h=o.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_sha256"); self.assertEqual(h,sha256_of(o))
    def test_deterministic_id(self): self.assertEqual(self.build()["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id"],self.build()["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id"])
    def test_no_mutations(self):
        o=self.build()
        for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created"): self.assertEqual(o[k],0)
    def test_no_live(self):
        o=self.build()
        for k in ("broker_routing_allowed","network_allowed","approved_for_live","network_used"): self.assertFalse(o[k])
    def test_source_not_mutated(self):
        s=src(); b=copy.deepcopy(s); build_verification(s,cfg()); self.assertEqual(s,b)
    def test_tampered_source(self):
        s=src(); s["cycle_id"]="BAD"
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateVerificationError,build_verification,s,cfg())
    def test_tampered_manifest(self):
        s=src(); s["certificate_manifest"]["certificate_effect"]="BAD"
        s["certificate_manifest_sha256"]=sha256_of(s["certificate_manifest"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateVerificationError,build_verification,s,cfg())
    def test_tampered_index(self):
        s=src(); s["certified_index"][0]["notional_value"]=1
        s["certified_index_sha256"]=sha256_of(s["certified_index"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateVerificationError,build_verification,s,cfg())
    def test_wrong_certificate_id(self):
        s=src(); s["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id"]="FSC-BAD"
        s["certificate_manifest"]["certificate_id"]="FSC-BAD"
        for x in s["certificate_ledger"]: x["certificate_id"]="FSC-BAD"
        s["certificate_manifest_sha256"]=sha256_of(s["certificate_manifest"])
        s["certificate_ledger_sha256"]=sha256_of(s["certificate_ledger"]); self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateVerificationError,build_verification,s,cfg())
    def test_settlement_rejected(self):
        s=src(); s["settlements_created"]=1; self.rehash(s)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateVerificationError,build_verification,s,cfg())
    def test_unsafe_config(self):
        c=cfg(); c["network_allowed"]=True
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateVerificationError,build_verification,src(),c)
    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src()),encoding="utf-8"); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            rc=main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")])
            self.assertEqual(rc,0); self.assertTrue((p/"out/offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_v75_2ap.json").exists())
    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()),encoding="utf-8")
            self.assertEqual(main(["--input",str(p/"missing.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
