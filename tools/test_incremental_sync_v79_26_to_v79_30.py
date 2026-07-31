import tempfile, unittest
from pathlib import Path
from alpaca_market_data import (
    IncrementalSyncConfig, IngestionBar, build_checkpoints,
    merge_incremental_rows, detect_missing_bars, build_gap_fill_queue,
    run_incremental_sync, build_incremental_sync_certificate,
)
def bar(symbol, minute, close=100):
    return IngestionBar(
      symbol=symbol,timestamp=f"2026-01-01T00:{minute:02d}:00Z",timeframe="1Min",
      open=close,high=close+1,low=close-1,close=close,volume=10
    )
class Tests(unittest.TestCase):
    def setUp(self):
        self.config=IncrementalSyncConfig(expected_symbols=("AAPL","MSFT"))
        self.existing=[bar("AAPL",0),bar("AAPL",1),bar("MSFT",0,200)]
    def test_v79_26_config_safety(self):
        self.config.validate(); self.assertFalse(self.config.allow_network)
    def test_v79_26_rejects_network(self):
        with self.assertRaises(ValueError): IncrementalSyncConfig(allow_network=True).validate()
    def test_v79_26_checkpoints(self):
        cp=build_checkpoints(self.existing)
        self.assertEqual(cp["AAPL"].last_timestamp,"2026-01-01T00:01:00Z")
    def test_v79_27_adds_new_rows(self):
        rows,stats=merge_incremental_rows(self.existing,[bar("AAPL",2)])
        self.assertEqual(stats["new_row_count"],1); self.assertEqual(len(rows),4)
    def test_v79_27_ignores_identical_duplicate(self):
        rows,stats=merge_incremental_rows(self.existing,[bar("AAPL",1)])
        self.assertEqual(stats["duplicate_row_count"],1); self.assertEqual(len(rows),3)
    def test_v79_27_conflict_rejected(self):
        with self.assertRaises(ValueError):
            merge_incremental_rows(self.existing,[bar("AAPL",1,101)])
    def test_v79_28_detects_gap(self):
        gaps=detect_missing_bars([bar("AAPL",0),bar("AAPL",2)])
        self.assertEqual(gaps[0][3],1)
    def test_v79_28_builds_queue(self):
        gaps=detect_missing_bars([bar("AAPL",0),bar("AAPL",3)])
        tasks=build_gap_fill_queue(gaps,self.config)
        self.assertEqual(tasks[0].expected_bar_count,2)
    def test_v79_29_run_sync(self):
        with tempfile.TemporaryDirectory() as t:
            result=run_incremental_sync(
              self.existing,[bar("AAPL",3),bar("MSFT",2,201)],
              self.config,Path(t))
            self.assertEqual(result["status"],"PASS")
            self.assertGreater(result["gap_task_count"],0)
    def test_v79_29_tamper_manifest_file_detected(self):
        from alpaca_market_data.incremental_sync_v79_26_30 import verify_incremental_manifest
        with tempfile.TemporaryDirectory() as t:
            result=run_incremental_sync(
              self.existing,[bar("AAPL",3),bar("MSFT",2,201)],
              self.config,Path(t))
            p=Path(t)/result["manifest"]["files"]["dataset"]["relative_path"]
            p.write_text("tampered")
            with self.assertRaises(ValueError):
                verify_incremental_manifest(Path(t),result["manifest"])
    def test_v79_30_certificate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            p=root/"release/v79_25/output/historical_ingestion_certificate_v79_25.json"
            p.parent.mkdir(parents=True); p.write_text('{"status":"PASS"}')
            result=run_incremental_sync(
              self.existing,[bar("AAPL",3),bar("MSFT",2,201)],
              self.config,root/"sync")
            cert=build_incremental_sync_certificate(
              root,root/"release/v79_30/output",self.config,result)
            self.assertEqual(cert["status"],"PASS")
            self.assertEqual(cert["actual_orders_submitted"],0)
    def test_no_trading_or_order_reference(self):
        text=(Path(__file__).resolve().parents[1]/"alpaca_market_data/incremental_sync_v79_26_30.py").read_text()
        self.assertNotIn("TradingClient",text)
        self.assertNotIn("submit_order(",text)
if __name__=="__main__": unittest.main()
