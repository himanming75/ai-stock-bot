import json, tempfile, unittest
from pathlib import Path
from alpaca_market_data import (
    IngestionBar, IngestionConfig, HistoricalDatasetStore,
    normalize_ingestion_rows, deduplicate_ingestion_rows,
    validate_ingestion_dataset, run_historical_ingestion,
    build_ingestion_certificate,
)
class Tests(unittest.TestCase):
    def setUp(self):
        self.config=IngestionConfig(expected_symbols=("AAPL","MSFT"))
        self.rows=[
          {"symbol":"AAPL","timestamp":"2026-01-01T00:00:00Z","open":100,"high":101,"low":99,"close":100.5,"volume":10},
          {"symbol":"AAPL","timestamp":"2026-01-01T00:01:00Z","open":100.5,"high":102,"low":100,"close":101.5,"volume":11},
          {"symbol":"MSFT","timestamp":"2026-01-01T00:00:00Z","open":200,"high":201,"low":199,"close":200.5,"volume":12},
        ]
    def test_v79_21_config_safety(self):
        self.config.validate()
        self.assertFalse(self.config.allow_network)
        self.assertFalse(self.config.allow_order_submission)
    def test_v79_21_rejects_network(self):
        with self.assertRaises(ValueError): IngestionConfig(allow_network=True).validate()
    def test_v79_22_normalizes_symbols_and_utc(self):
        rows=normalize_ingestion_rows([dict(self.rows[0],symbol="aapl",timestamp="2026-01-01T00:00:00")],self.config)
        self.assertEqual(rows[0].symbol,"AAPL"); self.assertTrue(rows[0].timestamp.endswith("Z"))
    def test_v79_22_rejects_bad_ohlc(self):
        with self.assertRaises(ValueError):
            IngestionBar("AAPL","2026-01-01T00:00:00Z","1Min",100,99,98,100,1)
    def test_v79_22_duplicate_removal(self):
        rows=normalize_ingestion_rows(self.rows+[self.rows[0]],self.config)
        unique,count=deduplicate_ingestion_rows(rows)
        self.assertEqual(count,1); self.assertEqual(len(unique),3)
    def test_v79_22_conflicting_duplicate_rejected(self):
        other=dict(self.rows[0],close=100.7)
        rows=normalize_ingestion_rows(self.rows+[other],self.config)
        with self.assertRaises(ValueError): deduplicate_ingestion_rows(rows)
    def test_v79_23_validation_passes(self):
        rows=normalize_ingestion_rows(self.rows,self.config)
        unique,count=deduplicate_ingestion_rows(rows)
        result=validate_ingestion_dataset(unique,self.config,count)
        self.assertEqual(result.status,"PASS")
    def test_v79_23_missing_symbol_fails(self):
        rows=normalize_ingestion_rows(self.rows[:2],self.config)
        result=validate_ingestion_dataset(rows,self.config)
        self.assertEqual(result.status,"FAIL")
    def test_v79_24_store_and_verify(self):
        with tempfile.TemporaryDirectory() as t:
            rows=normalize_ingestion_rows(self.rows,self.config)
            result=validate_ingestion_dataset(rows,self.config)
            store=HistoricalDatasetStore(Path(t))
            manifest=store.write(self.config,rows,result)
            self.assertTrue(store.verify(manifest))
    def test_v79_24_tamper_detected(self):
        with tempfile.TemporaryDirectory() as t:
            rows=normalize_ingestion_rows(self.rows,self.config)
            result=validate_ingestion_dataset(rows,self.config)
            store=HistoricalDatasetStore(Path(t)); manifest=store.write(self.config,rows,result)
            (Path(t)/manifest["files"]["jsonl"]["relative_path"]).write_text("tampered")
            with self.assertRaises(ValueError): store.verify(manifest)
    def test_ingestion_pipeline(self):
        with tempfile.TemporaryDirectory() as t:
            result=run_historical_ingestion(self.rows+[self.rows[0]],self.config,Path(t))
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["duplicate_count_removed"],1)
    def test_v79_25_certificate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            p=root/"release/v79_20/output/historical_network_smoke_certificate_v79_20.json"
            p.parent.mkdir(parents=True); p.write_text('{"status":"PASS"}')
            result=run_historical_ingestion(self.rows,self.config,root/"dataset")
            cert=build_ingestion_certificate(root,root/"release/v79_25/output",self.config,result)
            self.assertEqual(cert["status"],"PASS")
            self.assertEqual(cert["actual_orders_submitted"],0)
    def test_no_trading_client_or_order_reference(self):
        text=(Path(__file__).resolve().parents[1]/"alpaca_market_data/ingestion_v79_21_25.py").read_text()
        self.assertNotIn("TradingClient",text)
        self.assertNotIn("submit_order(",text)
if __name__=="__main__": unittest.main()
