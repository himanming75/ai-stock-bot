from pathlib import Path
import json,tempfile,unittest
from tools.discover_existing_backtest_and_build_feed import build,normalize_trade

class Tests(unittest.TestCase):
    def test_normalize_trade(self):
        x=normalize_trade({"ticker":"aapl","pnl":"1.25","reason":"target"},"x.json")
        self.assertEqual(x["symbol"],"AAPL")
        self.assertEqual(x["realized_pl"],1.25)
        self.assertEqual(x["exit_reason"],"target")

    def test_build_never_changes_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"backtest/results.json"
            p.parent.mkdir(parents=True)
            original=json.dumps({"trades":[{"symbol":"SPY","pnl":2.5}]})
            p.write_text(original,encoding="utf-8")
            r=build(root)
            self.assertEqual(p.read_text(encoding="utf-8"),original)
            self.assertFalse(r["contracts"]["existing_source_files_modified"])
            self.assertFalse(r["contracts"]["new_backtest_engine_created"])
            self.assertEqual(r["canonical_trade_count"],1)

    def test_empty_project_safe(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            self.assertEqual(r["canonical_trade_count"],0)
            self.assertEqual(r["next_state"],"NEEDS_EXISTING_REPLAY_CONNECTION")

if __name__=="__main__":
    unittest.main()
