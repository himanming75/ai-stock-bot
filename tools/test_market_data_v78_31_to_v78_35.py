import tempfile,unittest
from dataclasses import replace
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from market_data.market_data_pipeline_v78_31_35 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V78.30","status":"PASS",
          "certification_scope":"OFFLINE_MARKET_DATA_ADAPTER_DEVELOPMENT_ONLY",
          "champion_candidate":{"candidate_id":"abc"}})
        write_json(self.cfg,{"market_data":{"timezone":"America/New_York","symbols":["AAPL"],
          "timeframes":["1m"],"expected_interval_minutes":1}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o31=self.r/"o31";a=build_market_data_foundation(self.cert,self.cfg,o31)
        o32=self.r/"o32";b=run_offline_quote_bar_feed(o31/"market_data_adapter_foundation_v78_31.json",o32)
        o33=self.r/"o33";c=run_market_data_validation(o31/"market_data_adapter_foundation_v78_31.json",
            o32/"offline_quote_bar_feed_v78_32.json",o33)
        o34=self.r/"o34";d=run_market_data_safety_gate(o31/"market_data_adapter_foundation_v78_31.json",
            o32/"offline_quote_bar_feed_v78_32.json",o33/"market_data_validation_gap_detection_v78_33.json",o34)
        o35=self.r/"o35";e=issue_market_data_certificate(
            o31/"market_data_adapter_foundation_verification_v78_31.json",
            o32/"offline_quote_bar_feed_verification_v78_32.json",
            o33/"market_data_validation_gap_detection_verification_v78_33.json",
            o34/"market_data_safety_gate_verification_v78_34.json",
            o31/"market_data_adapter_foundation_v78_31.json",o35)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_invalid_quote_blocked(self):
        a=OfflineMarketDataAdapter();tz=ZoneInfo("America/New_York")
        with self.assertRaises(ValueError):a.make_quote("AAPL",datetime(2026,7,6,9,30,tzinfo=tz),101,100,1,1)
    def test_invalid_ohlc_blocked(self):
        a=OfflineMarketDataAdapter();tz=ZoneInfo("America/New_York")
        with self.assertRaises(ValueError):a.make_bar("AAPL",datetime(2026,7,6,9,30,tzinfo=tz),"1m",100,99,98,100,1)
    def test_duplicate_bar_blocked(self):
        a=OfflineMarketDataAdapter();tz=ZoneInfo("America/New_York")
        b=a.make_bar("AAPL",datetime(2026,7,6,9,30,tzinfo=tz),"1m",100,101,99,100,1)
        a.append_bar(b)
        with self.assertRaises(ValueError):a.append_bar(b)
    def test_bar_hash_tamper_blocked(self):
        a=OfflineMarketDataAdapter();tz=ZoneInfo("America/New_York")
        b=a.make_bar("AAPL",datetime(2026,7,6,9,30,tzinfo=tz),"1m",100,101,99,100,1)
        with self.assertRaises(ValueError):a.append_bar(replace(b,close=100.5))
    def test_gap_detection(self):
        tz=ZoneInfo("America/New_York");a=OfflineMarketDataAdapter()
        b1=a.make_bar("AAPL",datetime(2026,7,6,9,30,tzinfo=tz),"1m",100,101,99,100,1)
        b2=a.make_bar("AAPL",datetime(2026,7,6,9,33,tzinfo=tz),"1m",100,101,99,100,1)
        self.assertEqual(validate_market_data([], [b1,b2],1)["gap_count"],1)
    def test_naive_timestamp_blocked(self):
        with self.assertRaises(ValueError):
            OfflineMarketDataAdapter().make_quote("AAPL",datetime(2026,7,6,9,30),100,101,1,1)
    def test_certificate_scope(self):
        c=self.chain()[4];self.assertEqual(c["certification_scope"],"OFFLINE_STRATEGY_RUNTIME_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.30","status":"FAIL"})
        self.assertEqual(build_market_data_foundation(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0);self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
