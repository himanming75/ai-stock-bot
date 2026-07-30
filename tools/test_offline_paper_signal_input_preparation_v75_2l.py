import json, tempfile, unittest
from pathlib import Path
from tools.offline_paper_signal_input_preparation_v75_2l import (
    SignalInputPreparationError, build_preparation, main, preparation_id, sha256_of
)
PREPARED_AT = "2026-07-30T21:10:00+00:00"

def source_fixture():
    checks=[{"check_index":1,"check":"A","state":"PASS"}]
    ledger=[{"ledger_index":1,"event":"A","state":"PASS","certificate_id":"PBC-A"}]
    snap={"baseline_observed_at":"2026-07-30T21:00:00+00:00","broker_connected":False,
          "champion_candidate_id":"CAND-A","cycle_id":"PCS-A","cycle_sequence":1,
          "fill_simulation_started":False,"live_orders_enabled":False,"mode":"OFFLINE_PAPER",
          "network_enabled":False,"order_generation_started":False,"order_queue":[],
          "orders_submitted":0,"positions_mutated":False,"session_id":"PAPER-A",
          "signal_generation_started":False,"started_at":"2026-07-30T20:50:00+00:00","state":"ACTIVE"}
    s={"status":"PASS","decision":"offline_paper_cycle_runtime_baseline_certified",
       "certificate_id":"PBC-A","certificate_state":"READY_FOR_SIGNAL_INPUT_PREPARATION",
       "execution_id":"PCS-A","session_id":"PAPER-A","cycle_id":"PCS-A","cycle_sequence":1,
       "champion_candidate_id":"CAND-A","cycle_active":True,
       "baseline_checks":checks,"baseline_checks_sha256":sha256_of(checks),
       "baseline_ledger":ledger,"baseline_ledger_sha256":sha256_of(ledger),
       "baseline_snapshot":snap,"baseline_snapshot_sha256":sha256_of(snap),
       "baseline_gate":{"runtime_baseline_certified":True,"signal_input_preparation_allowed":True,
          "signal_generation_allowed":False,"order_generation_allowed":False,
          "fill_simulation_allowed":False,"paper_orders_allowed":False,
          "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2L"},
       "paper_orders_allowed":False,"live_orders_allowed":False,"network_allowed":False,
       "broker_connection_allowed":False,"orders_submitted":0,"approved_for_live":False,
       "network_used":False,"safety_lock":{"broker_connected":False,
          "broker_credentials_required":False,"external_side_effects_allowed":False,
          "live_orders_enabled":False,"live_trading_approval_allowed":False,
          "lock_state":"ENFORCED","network_enabled":False},
       "schema_version":"v75.2k.offline_paper_cycle_runtime_baseline_certificate.1","version":"75.2K"}
    s["offline_paper_cycle_runtime_baseline_certificate_sha256"]=sha256_of(s)
    return s

def config_fixture():
    return {"input_mode":"STATIC_OFFLINE_FIXTURE","symbols":["SPY"],
      "market_bars":[
        {"symbol":"SPY","timestamp":"2026-07-29T20:00:00+00:00","open":630.0,"high":632.0,"low":629.0,"close":631.0,"volume":1000000},
        {"symbol":"SPY","timestamp":"2026-07-30T14:30:00+00:00","open":631.0,"high":633.0,"low":630.5,"close":632.5,"volume":1200000},
        {"symbol":"SPY","timestamp":"2026-07-30T15:30:00+00:00","open":632.5,"high":634.0,"low":632.0,"close":633.5,"volume":900000}],
      "strategy_inputs":{"strategy_id":"CHAMPION_OFFLINE_V1","fast_window":2,"slow_window":3,
        "price_field":"close","minimum_history_bars":3},
      "signal_generation_allowed":False,"order_generation_allowed":False,
      "fill_simulation_allowed":False,"paper_orders_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"external_side_effects_allowed":False}

class TestV752L(unittest.TestCase):
    def build(self): return build_preparation(source_fixture(),config_fixture(),PREPARED_AT)
    @staticmethod
    def rehash(s):
        s.pop("offline_paper_cycle_runtime_baseline_certificate_sha256",None)
        s["offline_paper_cycle_runtime_baseline_certificate_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_version_schema(self):
        x=self.build(); self.assertEqual(x["version"],"75.2L")
        self.assertEqual(x["schema_version"],"v75.2l.offline_paper_signal_input_preparation.1")
    def test_state(self): self.assertEqual(self.build()["preparation_state"],"READY_FOR_SIGNAL_INPUT_VALIDATION")
    def test_prepared(self): self.assertTrue(self.build()["preparation_gate"]["signal_input_prepared"])
    def test_validation_allowed(self): self.assertTrue(self.build()["preparation_gate"]["signal_input_validation_allowed"])
    def test_signal_blocked(self): self.assertFalse(self.build()["preparation_gate"]["signal_generation_allowed"])
    def test_orders_blocked(self): self.assertFalse(self.build()["preparation_gate"]["order_generation_allowed"])
    def test_live_blocked(self): self.assertFalse(self.build()["live_orders_allowed"])
    def test_network_blocked(self): self.assertFalse(self.build()["network_allowed"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_submitted"],0)
    def test_bar_count(self): self.assertEqual(self.build()["signal_input_package"]["market_data"]["bar_count"],3)
    def test_immutable(self): self.assertTrue(self.build()["signal_input_package"]["market_data"]["immutable"])
    def test_checks(self): self.assertEqual(len(self.build()["preparation_checks"]),10)
    def test_ledger(self): self.assertEqual(len(self.build()["preparation_ledger"]),5)
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_signal_input_preparation_sha256"); self.assertEqual(h,sha256_of(x))
    def test_deterministic_id(self): self.assertEqual(preparation_id("A","B"),preparation_id("A","B"))
    def test_bad_source_integrity(self):
        s=source_fixture(); s["cycle_id"]="BAD"
        self.assertRaises(SignalInputPreparationError,build_preparation,s,config_fixture(),PREPARED_AT)
    def test_bad_state(self):
        s=source_fixture(); s["certificate_state"]="BAD"; self.rehash(s)
        self.assertRaises(SignalInputPreparationError,build_preparation,s,config_fixture(),PREPARED_AT)
    def test_duplicate_symbols(self):
        c=config_fixture(); c["symbols"]=["SPY","SPY"]
        self.assertRaises(SignalInputPreparationError,build_preparation,source_fixture(),c,PREPARED_AT)
    def test_bad_ohlc(self):
        c=config_fixture(); c["market_bars"][0]["low"]=700
        self.assertRaises(SignalInputPreparationError,build_preparation,source_fixture(),c,PREPARED_AT)
    def test_duplicate_bar(self):
        c=config_fixture(); c["market_bars"].append(dict(c["market_bars"][0]))
        self.assertRaises(SignalInputPreparationError,build_preparation,source_fixture(),c,PREPARED_AT)
    def test_missing_strategy(self):
        c=config_fixture(); c["strategy_inputs"]={}
        self.assertRaises(SignalInputPreparationError,build_preparation,source_fixture(),c,PREPARED_AT)
    def test_unsafe_config(self):
        c=config_fixture(); c["signal_generation_allowed"]=True
        self.assertRaises(SignalInputPreparationError,build_preparation,source_fixture(),c,PREPARED_AT)
    def test_nonempty_queue(self):
        s=source_fixture(); s["baseline_snapshot"]["order_queue"]=[1]
        s["baseline_snapshot_sha256"]=sha256_of(s["baseline_snapshot"]); self.rehash(s)
        self.assertRaises(SignalInputPreparationError,build_preparation,s,config_fixture(),PREPARED_AT)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(source_fixture()),encoding="utf-8")
            (p/"c.json").write_text(json.dumps(config_fixture()),encoding="utf-8")
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),
                                   "--output-dir",str(p/"out"),"--prepared-at",PREPARED_AT]),0)
            self.assertTrue((p/"out"/"offline_paper_signal_input_preparation_v75_2l.json").is_file())
            self.assertEqual(main(["--input",str(p/"missing.json"),"--config",str(p/"c.json"),
                                   "--output-dir",str(p/"bad")]),1)
    def test_package_hash(self):
        x=self.build(); self.assertEqual(x["signal_input_package_sha256"],sha256_of(x["signal_input_package"]))

if __name__=="__main__": unittest.main()
