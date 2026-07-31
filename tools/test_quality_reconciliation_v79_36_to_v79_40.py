from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from alpaca_market_data import (
    IngestionBar, QualityConfig, build_quality_certificate,
    build_repair_ledger, reconcile_symbol_time_series,
    run_quality_reconciliation, scan_dataset_integrity,
    validate_ohlcv, verify_quality_manifest,
)

def bar(symbol, minute, price):
    return IngestionBar(
        symbol=symbol,timeframe="1Min",
        timestamp=f"2026-01-05T14:{minute}:00Z",
        open=price,high=price+1,low=price-1,close=price+0.5,
        volume=100,trade_count=10,vwap=price+0.25,source="offline_fixture",
    )

class Tests(unittest.TestCase):
    def setUp(self):
        self.config=QualityConfig()
        self.rows=[]
        for symbol,price in (("AAPL",250),("MSFT",470),("SPY",610)):
            self.rows.extend([bar(symbol,"31",price),bar(symbol,"32",price+1),bar(symbol,"33",price+2)])

    def test_v79_36_config_safety(self):
        self.config.validate()
        with self.assertRaises(ValueError): QualityConfig(allow_network=True).validate()

    def test_v79_36_integrity_pass(self):
        issues,stats=scan_dataset_integrity(self.rows,self.config)
        self.assertEqual(issues,[])
        self.assertEqual(stats["duplicate_primary_key_count"],0)

    def test_v79_36_duplicate_detected(self):
        issues,_=scan_dataset_integrity(self.rows+[self.rows[0]],self.config)
        self.assertTrue(any(i.code=="DUPLICATE_PRIMARY_KEY" for i in issues))

    def test_v79_37_ohlcv_pass(self):
        issues,stats=validate_ohlcv(self.rows)
        self.assertEqual(issues,[])
        self.assertEqual(sum(stats.values()),0)

    def test_v79_37_bad_high_rejected_by_model(self):
        with self.assertRaises(ValueError):
            IngestionBar(**{**self.rows[0].to_dict(), "high": 1})

    def test_v79_37_negative_volume_rejected_by_model(self):
        with self.assertRaises(ValueError):
            IngestionBar(**{**self.rows[0].to_dict(), "volume": -1})

    def test_v79_38_reconciliation_pass(self):
        issues,stats=reconcile_symbol_time_series(self.rows,self.config)
        self.assertEqual(issues,[])
        self.assertEqual(stats["gap_count"],0)

    def test_v79_38_gap_detected(self):
        rows=[row for row in self.rows if not (row.symbol=="AAPL" and row.timestamp.endswith("14:32:00Z"))]
        issues,_=reconcile_symbol_time_series(rows,self.config)
        self.assertTrue(any(i.code=="NON_CONTIGUOUS_SERIES" for i in issues))

    def test_v79_38_out_of_order_detected(self):
        rows=list(self.rows); rows[0],rows[1]=rows[1],rows[0]
        issues,_=reconcile_symbol_time_series(rows,self.config)
        self.assertTrue(any(i.code=="OUT_OF_ORDER_SERIES" for i in issues))

    def test_v79_39_empty_repair_ledger(self):
        ledger=build_repair_ledger([])
        self.assertEqual(ledger["pending_repair_count"],0)

    def test_v79_39_manifest_and_tamper(self):
        with TemporaryDirectory() as tmp:
            output=Path(tmp)
            result=run_quality_reconciliation(self.rows,self.config,output)
            self.assertTrue(verify_quality_manifest(output,result["manifest"]))
            path=output/"alpaca_historical_bars.quality_report.json"
            path.write_text("{}\n",encoding="utf-8")
            with self.assertRaises(ValueError): verify_quality_manifest(output,result["manifest"])

    def test_v79_40_certificate(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            prior=root/"release/v79_35/output"
            prior.mkdir(parents=True)
            (prior/"historical_gap_fill_certificate_v79_35.json").write_text("{}\n")
            result=run_quality_reconciliation(self.rows,self.config,root/"release/v79_40/output/quality")
            cert=build_quality_certificate(root,root/"release/v79_40/output",self.config,result)
            self.assertEqual(cert["status"],"PASS")
            self.assertEqual(cert["quality_summary"]["issue_count"],0)

    def test_no_order_submission_or_credentials(self):
        source=(Path(__file__).resolve().parents[1]/"alpaca_market_data/quality_reconciliation_v79_36_40.py").read_text().lower()
        self.assertNotIn("submit_order(",source)
        self.assertNotIn("tradingclient(",source)
        self.assertNotIn("api_secret",source)

if __name__=="__main__": unittest.main()
