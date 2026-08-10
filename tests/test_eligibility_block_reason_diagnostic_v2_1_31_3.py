from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.eligibility_block_reason_diagnostic_v2_1_31_3 import (
    EligibilityBlockReasonDiagnosticV21313,
)
from broker_integration_v1.eligibility_block_reason_diagnostic_status_v2_1_31_3 import (
    build_v2_1_31_3_status,
)


class Tests(unittest.TestCase):
    def test_waiting_without_shadow(self):
        with tempfile.TemporaryDirectory() as td:
            r=EligibilityBlockReasonDiagnosticV21313(td).run()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_CANONICAL_REAL_MARKET_SHADOW"
            )
            self.assertFalse(r["execution_selector_modified"])
            self.assertFalse(r["thresholds_modified"])

    def test_real_selector_explanations(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=(
                root/"runtime"/"real_market_multitimeframe_shadow"/
                "latest_real_market_shadow.json"
            )
            source.parent.mkdir(parents=True,exist_ok=True)
            report={
                "canonical_engine":"multi_timeframe_ai.engine.analyze_symbol",
                "canonical_selector":"paper_autonomous_execution.signals.select_candidate",
                "generated_at_utc":"2026-08-10T18:00:00Z",
                "thresholds":{
                    "min_confidence":0.75,
                    "min_reward_risk":1.0,
                },
                "analyses":[
                    {
                        "symbol":"AAPL",
                        "action":"HOLD",
                        "reward_risk":1.2,
                        "execution_mode":"ANALYSIS_ONLY",
                        "confidence_calibration":{
                            "calibrated_confidence":0.80
                        },
                        "timeframes":[],
                    },
                    {
                        "symbol":"MSFT",
                        "action":"BUY",
                        "reward_risk":0.8,
                        "execution_mode":"ANALYSIS_ONLY",
                        "confidence_calibration":{
                            "calibrated_confidence":0.70
                        },
                        "timeframes":[],
                    },
                    {
                        "symbol":"SPY",
                        "action":"BUY",
                        "reward_risk":1.2,
                        "execution_mode":"ANALYSIS_ONLY",
                        "confidence_calibration":{
                            "calibrated_confidence":0.80
                        },
                        "timeframes":[],
                    },
                ],
            }
            source.write_text(json.dumps(report),encoding="utf-8")
            c=EligibilityBlockReasonDiagnosticV21313(root)
            r=c.run()
            self.assertEqual(
                r["status"],
                "PASS_ELIGIBILITY_BLOCK_REASON_DIAGNOSTIC"
            )
            rows={x["symbol"]:x for x in r["symbols"]}
            self.assertIn(
                "ACTION_NOT_BUY_OR_SELL",
                rows["AAPL"]["block_reasons"]
            )
            self.assertIn(
                "CONFIDENCE_BELOW_CURRENT_SELECTOR",
                rows["MSFT"]["block_reasons"]
            )
            self.assertIn(
                "REWARD_RISK_BELOW_CURRENT_SELECTOR",
                rows["MSFT"]["block_reasons"]
            )
            self.assertTrue(rows["SPY"]["eligible"])
            self.assertEqual(r["eligible_count"],1)
            self.assertFalse(r["execution_selector_modified"])
            self.assertFalse(r["thresholds_modified"])
            self.assertFalse(r["broker_network_used"])

    def test_dedup_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=(
                root/"runtime"/"real_market_multitimeframe_shadow"/
                "latest_real_market_shadow.json"
            )
            source.parent.mkdir(parents=True,exist_ok=True)
            source.write_text(json.dumps({
                "canonical_engine":"multi_timeframe_ai.engine.analyze_symbol",
                "canonical_selector":"paper_autonomous_execution.signals.select_candidate",
                "generated_at_utc":"2026-08-10T18:00:00Z",
                "thresholds":{"min_confidence":0.75,"min_reward_risk":1.0},
                "analyses":[{
                    "symbol":"AAPL","action":"HOLD","reward_risk":0.5,
                    "execution_mode":"ANALYSIS_ONLY",
                    "confidence_calibration":{"calibrated_confidence":0.5},
                    "timeframes":[],
                }],
            }),encoding="utf-8")
            c=EligibilityBlockReasonDiagnosticV21313(root)
            a=c.run()
            b=c.run()
            self.assertTrue(a["new_ledger_row"])
            self.assertFalse(b["new_ledger_row"])

    def test_status_contract(self):
        s=build_v2_1_31_3_status()
        self.assertTrue(s["canonical_selector_reused"])
        self.assertTrue(s["symbol_level_block_reasons"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertFalse(s["thresholds_modified"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["paper_orders"],0)
        self.assertEqual(s["live_orders"],0)


if __name__=="__main__":
    unittest.main()
