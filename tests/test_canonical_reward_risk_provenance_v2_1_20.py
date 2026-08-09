from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.canonical_reward_risk_provenance_bridge_v2_1_20 import (
    CanonicalRewardRiskProvenanceBridgeV2120,
)
from broker_integration_v1.canonical_reward_risk_provenance_status_v2_1_20 import (
    build_v2_1_20_status,
)

def write_sources(root, side="BUY", canonical_action="BUY", rr=1.2, conf=0.80):
    root=Path(root)
    ep=root/"runtime"/"fresh_eligible_signal_evidence_v2_1_16"
    cp=root/"runtime"/"real_market_multitimeframe_shadow"
    ep.mkdir(parents=True,exist_ok=True)
    cp.mkdir(parents=True,exist_ok=True)

    evidence={
        "stage":"V2.1.16",
        "evidence_key":"ev1",
        "observed_at_utc":"2026-08-10T14:00:00+00:00",
        "observer_state":"OBSERVED_FRESH",
        "canonical_gate_aligned":True,
        "eligible_signal_count":1,
        "eligible_signals":[{
            "symbol":"AAPL","side":side,"quantity":"1",
            "strategy_id":"V79","source_confidence":"0.65",
        }],
        "signal_capture_allowed":True,
        "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
        "all_fresh":True,
        "evidence_only":True,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
    (ep/"eligible_signal_evidence.jsonl").write_text(json.dumps(evidence)+"\n",encoding="utf-8")

    report={
        "stage":"REAL_MARKET_MULTI_TIMEFRAME_SHADOW_ADAPTER_V1_2",
        "status":"PASS",
        "mode":"SHADOW_ANALYSIS_ONLY",
        "generated_at_utc":"2026-08-10T14:00:00+00:00",
        "source_dataset":"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "canonical_engine":"multi_timeframe_ai.engine.analyze_symbol",
        "canonical_selector":"paper_autonomous_execution.signals.select_candidate",
        "thresholds":{"min_confidence":0.75,"min_reward_risk":1.0},
        "analyses":[{
            "symbol":"AAPL",
            "action":canonical_action,
            "reward_risk":rr,
            "confidence_calibration":{"calibrated_confidence":conf},
            "consensus_score":0.5,
        }],
    }
    (cp/"latest_real_market_shadow.json").write_text(json.dumps(report),encoding="utf-8")

class Tests(unittest.TestCase):
    def test_valid_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            r=CanonicalRewardRiskProvenanceBridgeV2120(td).build()
            self.assertEqual(r["new_rows"],1)
            row=json.loads(Path(r["latest_output"]).read_text(encoding="utf-8"))
            s=row["eligible_signals"][0]
            self.assertEqual(s["source_reward_risk"],"1.2")
            self.assertEqual(s["source_confidence"],"0.8")
            self.assertTrue(s["canonical_provenance_valid"])
            self.assertFalse(row["reward_risk_formula_recomputed"])

    def test_side_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td,side="BUY",canonical_action="SELL")
            r=CanonicalRewardRiskProvenanceBridgeV2120(td).build()
            self.assertEqual(r["blocked_rows"],1)
            row=json.loads(Path(r["latest_output"]).read_text(encoding="utf-8"))
            self.assertFalse(row["canonical_reward_risk_provenance_valid"])

    def test_missing_snapshot_waits(self):
        with tempfile.TemporaryDirectory() as td:
            ep=Path(td)/"runtime"/"fresh_eligible_signal_evidence_v2_1_16"
            ep.mkdir(parents=True)
            (ep/"eligible_signal_evidence.jsonl").write_text("{}\n")
            r=CanonicalRewardRiskProvenanceBridgeV2120(td).build()
            self.assertEqual(r["status"],"WAITING_FOR_CANONICAL_REAL_MARKET_SNAPSHOT")

    def test_contract_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            p=Path(td)/"runtime"/"real_market_multitimeframe_shadow"/"latest_real_market_shadow.json"
            report=json.loads(p.read_text())
            report["thresholds"]["min_confidence"]=0.60
            p.write_text(json.dumps(report))
            r=CanonicalRewardRiskProvenanceBridgeV2120(td).build()
            self.assertEqual(r["status"],"BLOCKED_CANONICAL_SOURCE_CONTRACT")

    def test_status_safety(self):
        s=build_v2_1_20_status()
        self.assertEqual(s["canonical_min_confidence"],"0.75")
        self.assertEqual(s["canonical_min_reward_risk"],"1.0")
        self.assertFalse(s["reward_risk_formula_recomputed"])
        self.assertFalse(s["etrade_oauth_from_stage"])
        self.assertFalse(s["broker_order_submission_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
