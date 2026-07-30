import copy, json, tempfile, unittest
from pathlib import Path
from tools.offline_paper_signal_output_validator_v75_2p import *

TS="2026-07-30T21:30:00+00:00"

def source_fixture():
    sig={"symbol":"SPY","as_of":"2026-07-30T15:30:00+00:00","strategy_id":"CHAMPION_OFFLINE_V1",
         "signal_method":"SIMPLE_MOVING_AVERAGE_CROSSOVER","price_field":"close",
         "fast_window":2,"slow_window":3,"fast_sma":633.0,"slow_sma":632.3333333333,
         "latest_price":633.5,"action":"BUY"}
    sig["signal_id"]="SIG-"+sha256_of(signal_material(sig))[:16].upper()
    sig["order_created"]=False; sig["order_submitted"]=False
    summary={"signal_count":1,"buy_count":1,"sell_count":0,"hold_count":0,"symbols":["SPY"],
             "strategy_id":"CHAMPION_OFFLINE_V1","signal_method":"SIMPLE_MOVING_AVERAGE_CROSSOVER"}
    pkg={"signal_execution_id":"SGE-A","authorization_id":"SGA-A","validation_id":"SIV-A",
         "preparation_id":"SIP-A","session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,
         "champion_candidate_id":"CAND-A","executed_at":"2026-07-30T21:25:00+00:00",
         "signals":[sig],"signal_summary":summary,"immutable":True,"network_source":False,
         "orders_created":0,"orders_submitted":0}
    token={"authorization_id":"SGA-A","validation_id":"SIV-A","issued_at":"2026-07-30T21:20:00+00:00",
           "expires_at":"2026-07-30T21:35:00+00:00","nonce":"x","scope":"OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
           "token_sha256":"x","single_use":True,"consumed":True,"consumed_at":"2026-07-30T21:25:00+00:00","token_state":"CONSUMED"}
    checks=[{"check_index":1,"check":"A","state":"PASS"}]; ledger=[{"ledger_index":1,"event":"A","state":"PASS"}]
    s={"status":"PASS","execution_state":"READY_FOR_SIGNAL_OUTPUT_VALIDATION","authorization_state":"CONSUMED",
       "token_consumed":True,"signal_generation_executed":True,"signal_execution_id":"SGE-A",
       "authorization_id":"SGA-A","validation_id":"SIV-A","preparation_id":"SIP-A","certificate_id":"PBC-A",
       "execution_id":"PCS-A","session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,
       "champion_candidate_id":"CAND-A","consumed_authorization_token":token,
       "consumed_authorization_token_sha256":sha256_of(token),"execution_checks":checks,
       "execution_checks_sha256":sha256_of(checks),"execution_ledger":ledger,
       "execution_ledger_sha256":sha256_of(ledger),"signal_output_package":pkg,
       "signal_output_package_sha256":sha256_of(pkg),
       "execution_gate":{"signal_generation_executed":True,"signal_output_validation_allowed":True,
                         "order_generation_allowed":False,"fill_simulation_allowed":False,
                         "paper_orders_allowed":False,"live_orders_allowed":False,
                         "network_allowed":False,"next_version":"75.2P"},
       "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
       "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
       "orders_created":0,"orders_submitted":0,"approved_for_live":False,"network_used":False,
       "safety_lock":{"broker_connected":False,"broker_credentials_required":False,
                      "external_side_effects_allowed":False,"live_orders_enabled":False,
                      "live_trading_approval_allowed":False,"lock_state":"ENFORCED","network_enabled":False},
       "schema_version":"v75.2o.offline_paper_signal_generation_execution.1","version":"75.2O"}
    s["offline_paper_signal_generation_execution_sha256"]=sha256_of(s)
    return s

def config_fixture():
    return {"validation_scope":"OFFLINE_PAPER_SIGNAL_OUTPUT_ONLY",
      "expected_signal_method":"SIMPLE_MOVING_AVERAGE_CROSSOVER",
      "require_execution_integrity":True,"require_signal_package_integrity":True,
      "require_consumed_token":True,"require_signal_id_recalculation":True,
      "require_sma_recalculation":True,"require_zero_orders":True,"require_network_disabled":True,
      "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False}

class TestV752P(unittest.TestCase):
    def build(self): return build_validation(source_fixture(),config_fixture(),TS)
    def rehash(self,s):
        s.pop("offline_paper_signal_generation_execution_sha256",None)
        s["offline_paper_signal_generation_execution_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["validation_state"],"READY_FOR_ORDER_INTENT_AUTHORIZATION")
    def test_signal(self): self.assertEqual(self.build()["validated_signals"][0]["action"],"BUY")
    def test_summary(self): self.assertEqual(self.build()["validated_signal_summary"]["buy_count"],1)
    def test_gate(self): self.assertTrue(self.build()["validation_gate"]["order_intent_authorization_allowed"])
    def test_order_blocked(self): self.assertFalse(self.build()["order_generation_allowed"])
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_signal_output_validation_sha256"); self.assertEqual(h,sha256_of(x))
    def test_checks(self): self.assertEqual(len(self.build()["validation_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["validation_ledger"]),6)
    def test_bad_integrity(self):
        s=source_fixture(); s["cycle_id"]="BAD"
        self.assertRaises(SignalOutputValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_action(self):
        s=source_fixture(); s["signal_output_package"]["signals"][0]["action"]="SELL"
        s["signal_output_package_sha256"]=sha256_of(s["signal_output_package"]); self.rehash(s)
        self.assertRaises(SignalOutputValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_signal_id(self):
        s=source_fixture(); s["signal_output_package"]["signals"][0]["signal_id"]="BAD"
        s["signal_output_package_sha256"]=sha256_of(s["signal_output_package"]); self.rehash(s)
        self.assertRaises(SignalOutputValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_summary(self):
        s=source_fixture(); s["signal_output_package"]["signal_summary"]["buy_count"]=0
        s["signal_output_package_sha256"]=sha256_of(s["signal_output_package"]); self.rehash(s)
        self.assertRaises(SignalOutputValidationError,build_validation,s,config_fixture(),TS)
    def test_unconsumed(self):
        s=source_fixture(); s["token_consumed"]=False; self.rehash(s)
        self.assertRaises(SignalOutputValidationError,build_validation,s,config_fixture(),TS)
    def test_orders(self):
        s=source_fixture(); s["orders_created"]=1; self.rehash(s)
        self.assertRaises(SignalOutputValidationError,build_validation,s,config_fixture(),TS)
    def test_network(self):
        s=source_fixture(); s["network_allowed"]=True; self.rehash(s)
        self.assertRaises(SignalOutputValidationError,build_validation,s,config_fixture(),TS)
    def test_bad_config(self):
        c=config_fixture(); c["order_generation_allowed"]=True
        self.assertRaises(SignalOutputValidationError,build_validation,source_fixture(),c,TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(source_fixture())); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--validated-at",TS]),0)
            self.assertTrue((p/"out"/"offline_paper_signal_output_validation_v75_2p.json").exists())
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input",str(p/"missing"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
