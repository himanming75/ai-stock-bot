from pathlib import Path
import json,tempfile,unittest
from tools.build_backtest_provenance_quality_gate import classify_source,build

class Tests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(classify_source("release/v69_1/scenarios/paper_trade_scenarios_momentum_v69_1.json"),"SYNTHETIC_SCENARIO")
        self.assertEqual(classify_source("release/x/fixture.json"),"FIXTURE")
        self.assertEqual(classify_source("release/x/example.jsonl"),"EXAMPLE")
        self.assertEqual(classify_source("runtime/backtest_v2/results.jsonl"),"REAL_HISTORICAL_BACKTEST")

    def test_synthetic_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"runtime/canonical_backtest_feed/canonical_backtest_trades.jsonl"
            p.parent.mkdir(parents=True)
            row={"symbol":"AAPL","realized_pl":1.2,"entry_time":"2026-01-01","exit_time":"2026-01-02","_canonical_source":"release/v69_1/scenarios/paper_trade_scenarios_momentum_v69_1.json"}
            p.write_text(json.dumps(row)+"\n",encoding="utf-8")
            r=build(root)
            self.assertEqual(r["curated_record_count"],0)
            self.assertEqual(r["excluded_record_count"],1)

    def test_source_feed_not_modified(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"runtime/canonical_backtest_feed/canonical_backtest_trades.jsonl"
            p.parent.mkdir(parents=True)
            original=json.dumps({"symbol":"SPY","realized_pl":2,"entry_time":"2026-01-01","exit_time":"2026-01-02","_canonical_source":"runtime/backtest_v2/results.jsonl"})+"\n"
            p.write_text(original,encoding="utf-8")
            r=build(root)
            self.assertEqual(p.read_text(encoding="utf-8"),original)
            self.assertFalse(r["contracts"]["source_feed_modified"])

if __name__=="__main__":
    unittest.main()
