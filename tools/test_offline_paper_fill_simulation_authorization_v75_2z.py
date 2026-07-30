import copy,json,tempfile,unittest
from pathlib import Path
from tools.offline_paper_fill_simulation_authorization_v75_2z import *

TS="2026-07-30T22:20:00+00:00"

def cfg():
    return {
      "authorization_scope":"OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY",
      "authorization_ttl_seconds":900,
      "fill_price_policy":"REFERENCE_PRICE_ONLY",
      "fill_quantity_policy":"FULL_QUANTITY_ONLY",
      "require_validation_integrity":True,
      "require_validated_submissions_integrity":True,
      "require_zero_existing_fills":True,
      "require_single_use_token":True,
      "require_reference_price_lock":True,
      "require_quantity_lock":True,
      "fill_simulation_allowed":False,
      "position_update_allowed":False,
      "cash_update_allowed":False,
      "portfolio_update_allowed":False,
      "external_order_submission_allowed":False,
      "broker_routing_allowed":False,
      "paper_broker_allowed":False,
      "live_orders_allowed":False,
      "network_allowed":False,
      "broker_connection_allowed":False,
      "external_side_effects_allowed":False}

def src():
    submissions=[{
      "authorization_id":"OSA-A","broker_routed":False,"external_submission":False,
      "fill_simulated":False,"filled":False,"network_used":False,
      "offline_submission_id":"OSUB-AAAAAAAAAAAAAAAA",
      "order_intent_id":"INT-A","order_state":"SUBMITTED_OFFLINE_REFERENCE",
      "order_type":"MARKET_REFERENCE_ONLY","paper_order_id":"PORD-AAAAAAAAAAAAAAAA",
      "previous_order_state":"CREATED_NOT_SUBMITTED","quantity":1,
      "reference_price":633.5,"side":"BUY","submitted_offline":True,
      "symbol":"SPY","time_in_force":"DAY","validation_state":"PASS"}]
    checks=[{"check_index":1,"check":"A","state":"PASS"}]
    ledger=[{"ledger_index":1,"event":"A","state":"PASS","validation_id":"OSV-A"}]
    s={
      "status":"PASS","authorization_id":"OSA-A","authorization_source_id":"OGA-A",
      "broker_connection_allowed":False,"broker_routes_created":0,
      "broker_routing_allowed":False,"champion_candidate_id":"CAND-A",
      "cycle_id":"PCS-A","cycle_sequence":1,
      "decision":"offline_paper_order_submission_validated",
      "execution_id":"OGE-A","external_order_submission_allowed":False,
      "external_orders_submitted":0,"fill_simulation_allowed":False,
      "fills_created":0,"live_orders_allowed":False,"network_allowed":False,
      "network_used":False,"paper_broker_allowed":False,
      "safety_lock":{"broker_connected":False,"broker_credentials_required":False,
        "external_side_effects_allowed":False,"live_orders_enabled":False,
        "live_trading_approval_allowed":False,"lock_state":"ENFORCED",
        "network_enabled":False},
      "schema_version":"v75.2y.offline_paper_order_submission_validation.1",
      "session_id":"PAPER-A","source_order_submission_execution_sha256":"a"*64,
      "source_order_submission_authorization_sha256":"b"*64,
      "submission_execution_id":"OSE-A","submission_validated":True,
      "submission_validation_id":"OSV-A","validated_submission_count":1,
      "validated_submissions":submissions,
      "validated_submissions_sha256":sha256_of(submissions),
      "validation_checks":checks,"validation_checks_sha256":sha256_of(checks),
      "validation_gate":{"broker_routing_allowed":False,
        "external_order_submission_allowed":False,"fill_simulation_allowed":False,
        "fill_simulation_authorization_allowed":True,"live_orders_allowed":False,
        "network_allowed":False,"next_version":"75.2Z",
        "paper_broker_allowed":False,"submission_validated":True},
      "validation_id":"OOV-A","validation_ledger":ledger,
      "validation_ledger_sha256":sha256_of(ledger),
      "validation_state":"READY_FOR_FILL_SIMULATION_AUTHORIZATION",
      "version":"75.2Y","approved_for_live":False}
    s["offline_paper_order_submission_validation_sha256"]=sha256_of(s)
    return s

class TestV752Z(unittest.TestCase):
    def build(self): return build_authorization(src(),cfg(),TS)
    def rehash(self,s):
        s.pop("offline_paper_order_submission_validation_sha256",None)
        s["offline_paper_order_submission_validation_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["authorization_state"],"AUTHORIZED_NOT_EXECUTED")
    def test_scope(self): self.assertEqual(self.build()["authorization_scope"],"OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY")
    def test_count(self): self.assertEqual(self.build()["authorized_target_count"],1)
    def test_token(self):
        t=self.build()["fill_simulation_authorization_token"]
        self.assertFalse(t["consumed"]); self.assertTrue(t["single_use"])
    def test_ttl(self):
        x=self.build()
        self.assertEqual((parse_ts(x["expires_at"],"x")-parse_ts(x["issued_at"],"y")).total_seconds(),900)
    def test_target(self):
        o=self.build()["authorized_fill_simulation_targets"][0]
        self.assertEqual(o["fill_price_policy"],"REFERENCE_PRICE_ONLY")
        self.assertEqual(o["fill_quantity_policy"],"FULL_QUANTITY_ONLY")
        self.assertFalse(o["fill_object_created"])
    def test_gate(self):
        x=self.build()["authorization_gate"]
        self.assertTrue(x["fill_simulation_execution_allowed"])
        self.assertFalse(x["position_update_allowed"])
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_fill_simulation_authorization_sha256")
        self.assertEqual(h,sha256_of(x))
    def test_targets_hash(self):
        x=self.build()
        self.assertEqual(x["authorized_fill_simulation_targets_sha256"],sha256_of(x["authorized_fill_simulation_targets"]))
    def test_checks(self): self.assertEqual(len(self.build()["authorization_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["authorization_ledger"]),6)
    def test_bad_integrity(self):
        s=src(); s["cycle_id"]="BAD"
        self.assertRaises(FillSimulationAuthorizationError,build_authorization,s,cfg(),TS)
    def test_bad_state(self):
        s=src(); s["validation_state"]="BAD"; self.rehash(s)
        self.assertRaises(FillSimulationAuthorizationError,build_authorization,s,cfg(),TS)
    def test_existing_fill(self):
        s=src(); s["validated_submissions"][0]["filled"]=True
        s["validated_submissions_sha256"]=sha256_of(s["validated_submissions"]); self.rehash(s)
        self.assertRaises(FillSimulationAuthorizationError,build_authorization,s,cfg(),TS)
    def test_bad_price(self):
        s=src(); s["validated_submissions"][0]["reference_price"]=0
        s["validated_submissions_sha256"]=sha256_of(s["validated_submissions"]); self.rehash(s)
        self.assertRaises(FillSimulationAuthorizationError,build_authorization,s,cfg(),TS)
    def test_bad_quantity(self):
        s=src(); s["validated_submissions"][0]["quantity"]=0
        s["validated_submissions_sha256"]=sha256_of(s["validated_submissions"]); self.rehash(s)
        self.assertRaises(FillSimulationAuthorizationError,build_authorization,s,cfg(),TS)
    def test_bad_ttl(self):
        c=cfg(); c["authorization_ttl_seconds"]=30
        self.assertRaises(FillSimulationAuthorizationError,build_authorization,src(),c,TS)
    def test_unsafe_config(self):
        c=cfg(); c["position_update_allowed"]=True
        self.assertRaises(FillSimulationAuthorizationError,build_authorization,src(),c,TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/"s.json").write_text(json.dumps(src()))
            (p/"c.json").write_text(json.dumps(cfg()))
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),
                "--output-dir",str(p/"out"),"--issued-at",TS]),0)
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()))
            self.assertEqual(main(["--input",str(p/"missing"),"--config",str(p/"c.json"),
                "--output-dir",str(p/"out")]),1)

if __name__=="__main__":
    unittest.main()
