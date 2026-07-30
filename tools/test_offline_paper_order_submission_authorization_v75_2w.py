import copy,json,tempfile,unittest
from pathlib import Path
from tools.offline_paper_order_submission_authorization_v75_2w import *

TS="2026-07-30T22:05:00+00:00"

def cfg():
    return {"authorization_scope":"OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY",
      "authorization_ttl_seconds":900,"require_validation_integrity":True,
      "require_validated_orders_integrity":True,"require_zero_submissions":True,
      "require_zero_fills":True,"require_single_use_token":True,
      "order_submission_allowed":False,"broker_routing_allowed":False,
      "fill_simulation_allowed":False,"paper_broker_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"external_side_effects_allowed":False}

def src():
    orders=[{"authorization_id":"OGA-A","broker_routed":False,"fill_simulated":False,
      "filled":False,"network_used":False,"order_intent_id":"INT-A",
      "order_state":"CREATED_NOT_SUBMITTED","order_type":"MARKET_REFERENCE_ONLY",
      "paper_order_id":"PORD-AAAAAAAAAAAAAAAA","quantity":1,"reference_price":633.5,
      "side":"BUY","submitted":False,"symbol":"SPY","time_in_force":"DAY",
      "validation_state":"PASS"}]
    checks=[{"check_index":1,"check":"A","state":"PASS"}]
    ledger=[{"ledger_index":1,"event":"A","state":"PASS","validation_id":"OOV-A"}]
    s={"status":"PASS","validation_id":"OOV-A",
       "validation_state":"READY_FOR_ORDER_SUBMISSION_AUTHORIZATION",
       "order_objects_validated":True,"validated_order_count":1,
       "validated_orders":orders,"validated_orders_sha256":sha256_of(orders),
       "validation_checks":checks,"validation_checks_sha256":sha256_of(checks),
       "validation_ledger":ledger,"validation_ledger_sha256":sha256_of(ledger),
       "validation_gate":{"order_objects_validated":True,
         "order_submission_authorization_allowed":True,"order_submission_allowed":False,
         "fill_simulation_allowed":False,"paper_broker_allowed":False,
         "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2W"},
       "execution_id":"OGE-A","authorization_id":"OGA-A",
       "session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,
       "champion_candidate_id":"CAND-A",
       "source_order_generation_execution_sha256":"a"*64,
       "order_submission_allowed":False,"fill_simulation_allowed":False,
       "paper_broker_allowed":False,"live_orders_allowed":False,
       "network_allowed":False,"broker_connection_allowed":False,
       "orders_submitted":0,"fills_created":0,"approved_for_live":False,
       "network_used":False,"safety_lock":{"broker_connected":False,
       "broker_credentials_required":False,"external_side_effects_allowed":False,
       "live_orders_enabled":False,"live_trading_approval_allowed":False,
       "lock_state":"ENFORCED","network_enabled":False},
       "schema_version":"v75.2v.offline_paper_order_object_validation.1",
       "version":"75.2V"}
    s["offline_paper_order_object_validation_sha256"]=sha256_of(s)
    return s

class TestV752W(unittest.TestCase):
    def build(self): return build_authorization(src(),cfg(),TS)
    def rehash(self,s):
        s.pop("offline_paper_order_object_validation_sha256",None)
        s["offline_paper_order_object_validation_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["authorization_state"],"AUTHORIZED_NOT_EXECUTED")
    def test_scope(self): self.assertEqual(self.build()["authorization_scope"],"OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY")
    def test_count(self): self.assertEqual(self.build()["authorized_order_count"],1)
    def test_token(self):
        t=self.build()["authorization_token"]; self.assertFalse(t["consumed"]); self.assertTrue(t["single_use"])
    def test_ttl(self):
        x=self.build(); self.assertEqual((parse_ts(x["expires_at"],"x")-parse_ts(x["issued_at"],"y")).total_seconds(),900)
    def test_gate(self): self.assertTrue(self.build()["authorization_gate"]["submission_execution_allowed"])
    def test_still_blocked(self): self.assertFalse(self.build()["order_submission_allowed"])
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_order_submission_authorization_sha256")
        self.assertEqual(h,sha256_of(x))
    def test_manifest_hash(self):
        x=self.build(); self.assertEqual(x["authorized_order_manifest_sha256"],sha256_of(x["authorized_order_manifest"]))
    def test_checks(self): self.assertEqual(len(self.build()["authorization_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["authorization_ledger"]),6)
    def test_bad_integrity(self):
        s=src(); s["cycle_id"]="BAD"
        self.assertRaises(OrderSubmissionAuthorizationError,build_authorization,s,cfg(),TS)
    def test_bad_state(self):
        s=src(); s["validation_state"]="BAD"; self.rehash(s)
        self.assertRaises(OrderSubmissionAuthorizationError,build_authorization,s,cfg(),TS)
    def test_submitted(self):
        s=src(); s["validated_orders"][0]["submitted"]=True
        s["validated_orders_sha256"]=sha256_of(s["validated_orders"]); self.rehash(s)
        self.assertRaises(OrderSubmissionAuthorizationError,build_authorization,s,cfg(),TS)
    def test_bad_ttl(self):
        c=cfg(); c["authorization_ttl_seconds"]=30
        self.assertRaises(OrderSubmissionAuthorizationError,build_authorization,src(),c,TS)
    def test_unsafe_config(self):
        c=cfg(); c["order_submission_allowed"]=True
        self.assertRaises(OrderSubmissionAuthorizationError,build_authorization,src(),c,TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src())); (p/"c.json").write_text(json.dumps(cfg()))
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--issued-at",TS]),0)
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()))
            self.assertEqual(main(["--input",str(p/"missing"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
