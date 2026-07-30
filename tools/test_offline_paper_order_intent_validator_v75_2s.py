import copy,json,tempfile,unittest
from pathlib import Path
from tools.offline_paper_order_intent_validator_v75_2s import *

TS="2026-07-30T21:45:00+00:00"

def source_fixture():
    intent={"authorization_id":"OIA-A","broker_routed":False,"created_at":"2026-07-30T21:40:00+00:00",
            "fill_simulated":False,"intent_action":"BUY","intent_type":"MARKET_REFERENCE_ONLY",
            "network_used":False,"order_created":False,"order_submitted":False,"quantity":1,
            "reference_price":633.5,"signal_action":"BUY","signal_id":"SIG-A","symbol":"SPY"}
    intent["order_intent_id"]=expected_intent_id(intent["authorization_id"],intent["signal_id"],intent["created_at"])
    pkg={"execution_id":"OIE-A","authorization_id":"OIA-A","validation_id":"SOV-A","signal_execution_id":"SGE-A",
         "session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,"champion_candidate_id":"CAND-A",
         "created_at":"2026-07-30T21:40:00+00:00","order_intents":[intent],"order_intent_count":1,
         "immutable":True,"orders_created":0,"orders_submitted":0,"network_source":False}
    token={"authorization_id":"OIA-A","authorized_signal_ids":["SIG-A"],"consumed":True,
           "consumed_at":"2026-07-30T21:40:00+00:00","expires_at":"2026-07-30T21:50:00+00:00",
           "issued_at":"2026-07-30T21:35:00+00:00","nonce":"n","scope":"OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY",
           "single_use":True,"token_sha256":"x","token_state":"CONSUMED","validation_id":"SOV-A"}
    checks=[{"check_index":1,"check":"A","state":"PASS"}]; ledger=[{"ledger_index":1,"event":"A","state":"PASS"}]
    s={"status":"PASS","execution_id":"OIE-A","execution_state":"READY_FOR_ORDER_INTENT_VALIDATION",
       "authorization_id":"OIA-A","authorization_state":"CONSUMED","token_consumed":True,
       "consumed_authorization_token":token,"consumed_authorization_token_sha256":sha256_of(token),
       "order_intent_package":pkg,"order_intent_package_sha256":sha256_of(pkg),
       "execution_checks":checks,"execution_checks_sha256":sha256_of(checks),
       "execution_ledger":ledger,"execution_ledger_sha256":sha256_of(ledger),
       "order_intent_authorized":True,"order_intent_created":True,"order_intents_created":1,
       "validation_id":"SOV-A","signal_execution_id":"SGE-A","session_id":"PAPER-A",
       "cycle_id":"PCS-A","cycle_sequence":1,"champion_candidate_id":"CAND-A",
       "execution_gate":{"order_intent_created":True,"order_intent_validation_allowed":True,
                         "order_generation_allowed":False,"fill_simulation_allowed":False,
                         "paper_orders_allowed":False,"live_orders_allowed":False,
                         "network_allowed":False,"next_version":"75.2S"},
       "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
       "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
       "orders_created":0,"orders_submitted":0,"approved_for_live":False,"network_used":False,
       "safety_lock":{"broker_connected":False,"broker_credentials_required":False,
                      "external_side_effects_allowed":False,"live_orders_enabled":False,
                      "live_trading_approval_allowed":False,"lock_state":"ENFORCED","network_enabled":False},
       "schema_version":"v75.2r.offline_paper_order_intent_execution.1","version":"75.2R"}
    s["offline_paper_order_intent_execution_sha256"]=sha256_of(s)
    return s

def config_fixture():
    return {"validation_scope":"OFFLINE_PAPER_ORDER_INTENT_ONLY","expected_intent_type":"MARKET_REFERENCE_ONLY",
            "require_execution_integrity":True,"require_package_integrity":True,"require_consumed_token":True,
            "require_intent_id_recalculation":True,"require_signal_intent_consistency":True,
            "require_positive_reference_price":True,"require_zero_orders":True,"require_safety_lock":True,
            "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
            "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False}

class TestV752S(unittest.TestCase):
    def build(self): return build_validation(source_fixture(),config_fixture(),TS)
    def rehash(self,s):
        s.pop("offline_paper_order_intent_execution_sha256",None)
        s["offline_paper_order_intent_execution_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["validation_state"],"READY_FOR_ORDER_GENERATION_AUTHORIZATION")
    def test_summary(self): self.assertEqual(self.build()["validated_order_intent_summary"]["buy_intent_count"],1)
    def test_intent(self):
        x=self.build()["validated_order_intents"][0]
        self.assertEqual(x["symbol"],"SPY"); self.assertEqual(x["quantity"],1)
    def test_gate(self): self.assertTrue(self.build()["validation_gate"]["order_generation_authorization_allowed"])
    def test_orders_blocked(self): self.assertFalse(self.build()["order_generation_allowed"])
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_order_intent_validation_sha256"); self.assertEqual(h,sha256_of(x))
    def test_checks(self): self.assertEqual(len(self.build()["validation_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["validation_ledger"]),6)
    def test_bad_integrity(self):
        s=source_fixture(); s["cycle_id"]="BAD"
        self.assertRaises(OrderIntentValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_intent_id(self):
        s=source_fixture(); s["order_intent_package"]["order_intents"][0]["order_intent_id"]="BAD"
        s["order_intent_package_sha256"]=sha256_of(s["order_intent_package"]); self.rehash(s)
        self.assertRaises(OrderIntentValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_action(self):
        s=source_fixture(); s["order_intent_package"]["order_intents"][0]["intent_action"]="SELL"
        s["order_intent_package_sha256"]=sha256_of(s["order_intent_package"]); self.rehash(s)
        self.assertRaises(OrderIntentValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_quantity(self):
        s=source_fixture(); s["order_intent_package"]["order_intents"][0]["quantity"]=2
        s["order_intent_package_sha256"]=sha256_of(s["order_intent_package"]); self.rehash(s)
        self.assertRaises(OrderIntentValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_price(self):
        s=source_fixture(); s["order_intent_package"]["order_intents"][0]["reference_price"]=0
        s["order_intent_package_sha256"]=sha256_of(s["order_intent_package"]); self.rehash(s)
        self.assertRaises(OrderIntentValidationError,build_validation,s,config_fixture(),TS)
    def test_order_side_effect(self):
        s=source_fixture(); s["order_intent_package"]["order_intents"][0]["order_created"]=True
        s["order_intent_package_sha256"]=sha256_of(s["order_intent_package"]); self.rehash(s)
        self.assertRaises(OrderIntentValidationError,build_validation,s,config_fixture(),TS)
    def test_unconsumed(self):
        s=source_fixture(); s["token_consumed"]=False; self.rehash(s)
        self.assertRaises(OrderIntentValidationError,build_validation,s,config_fixture(),TS)
    def test_unsafe_config(self):
        c=config_fixture(); c["order_generation_allowed"]=True
        self.assertRaises(OrderIntentValidationError,build_validation,source_fixture(),c,TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(source_fixture())); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--validated-at",TS]),0)
            self.assertTrue((p/"out"/"offline_paper_order_intent_validation_v75_2s.json").exists())
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input",str(p/"missing"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
