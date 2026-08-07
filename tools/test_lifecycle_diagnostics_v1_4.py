from pathlib import Path
import json, tempfile, unittest
from validation_analytics_v3 import (
    _rr_band_value, _hold_band_value, lifecycle_replay_diagnostics
)

class Tests(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(_rr_band_value(2.1),"2.00+")
        self.assertEqual(_rr_band_value(1.1),"1.00-1.25")
        self.assertEqual(_hold_band_value(30),"30m+")
        self.assertEqual(_hold_band_value(12),"10-20m")

    def test_empty_replay_is_safe_and_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            r=lifecycle_replay_diagnostics(root)
            self.assertEqual(r["status"],"COLLECTING_DATA")
            self.assertFalse(r["contracts"]["broker_write_performed"])
            self.assertFalse(r["contracts"]["strategy_parameter_changed"])
            self.assertFalse(r["contracts"]["automatic_parameter_optimization"])

    def test_mfe_mae_and_breakdown(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            hist=root/"runtime/real_historical_ingestion"
            hist.mkdir(parents=True)
            rows=[
                {"symbol":"AAPL","timestamp":"2026-08-03T13:31:00+00:00","open":100,"high":101,"low":99.5,"close":100.5,"volume":1},
                {"symbol":"AAPL","timestamp":"2026-08-03T13:32:00+00:00","open":100.5,"high":102,"low":100,"close":101,"volume":1},
            ]
            (hist/"alpaca_real_historical_1min.jsonl").write_text(
                "\n".join(json.dumps(x) for x in rows),encoding="utf-8"
            )
            out=root/"runtime/real_market_multitimeframe_shadow"
            out.mkdir(parents=True)
            replay={"closed_trades":[{
                "symbol":"AAPL",
                "entry_time_et":"2026-08-03T13:31:00+00:00",
                "exit_time_et":"2026-08-03T13:32:00+00:00",
                "entry_price":100.0,
                "exit_price":101.0,
                "realized_pl":1.0,
                "hold_minutes":1,
                "exit_reason":"TIME_EXIT",
                "entry_confidence":0.80,
                "entry_reward_risk":1.2,
            }]}
            (out/"latest_paper_lifecycle_replay.json").write_text(
                json.dumps(replay),encoding="utf-8"
            )
            r=lifecycle_replay_diagnostics(root)
            self.assertEqual(r["closed_trade_count"],1)
            self.assertAlmostEqual(r["enriched_trades"][0]["mfe_pct"],.02)
            self.assertAlmostEqual(r["enriched_trades"][0]["mae_pct"],-.005)
            self.assertEqual(r["breakdowns"]["symbol"][0]["group"],"AAPL")

    def test_no_duplicate_analytics_module(self):
        txt=Path("validation_analytics_v3.py").read_text(encoding="utf-8")
        self.assertIn("def lifecycle_replay_diagnostics(",txt)
        self.assertIn("_PRE_V14_MAIN_REPORT = main_report",txt)

if __name__=="__main__":
    unittest.main()
