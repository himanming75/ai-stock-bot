import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.market_data_pipeline_v77_26_30 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name);self.cert=self.r/"v77_25.json"
        write_json(self.cert,{"certificate_id":"SCHEDULED-RUNTIME-AUDIT-V77.25","status":"PASS","certificate_sha256":"abc"})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o26=self.r/"o26";s26=build_paper_market_data_feed(self.cert,o26,bar_count=10)
        feed=o26/"paper_market_data_feed_v77_26.json";o27=self.r/"o27";s27=build_market_data_validation_ledger(feed,o27)
        ledger=o27/"market_data_validation_ledger_v77_27.json";o28=self.r/"o28";s28=detect_stale_data_gaps(feed,ledger,o28)
        detector=o28/"stale_data_gap_detector_v77_28.json";o29=self.r/"o29";s29=recover_market_data(feed,detector,o29)
        o30=self.r/"o30";s30=issue_market_data_certificate(
            o26/"paper_market_data_feed_verification_v77_26.json",o27/"market_data_validation_ledger_verification_v77_27.json",
            o28/"stale_data_gap_detector_verification_v77_28.json",o29/"market_data_recovery_engine_verification_v77_29.json",o30)
        return s26,s27,s28,s29,s30
    def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
    def test_invalid_certificate(self):
        write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
        with self.assertRaises(MarketDataError):build_paper_market_data_feed(self.cert,self.r/"x")
    def test_invalid_feed_config(self):
        with self.assertRaises(MarketDataError):build_paper_market_data_feed(self.cert,self.r/"x",bar_count=1)
    def test_gap_detector_finds_gap(self):
        o26=self.r/"o26";build_paper_market_data_feed(self.cert,o26,bar_count=4)
        feed_path=o26/"paper_market_data_feed_v77_26.json";feed=load_json(feed_path)
        feed["bars"][2]["timestamp_utc"]="2026-01-02T14:35:00+00:00";write_json(feed_path,feed)
        o27=self.r/"o27";build_market_data_validation_ledger(feed_path,o27)
        result=detect_stale_data_gaps(feed_path,o27/"market_data_validation_ledger_v77_27.json",self.r/"o28")
        self.assertEqual(result.status,"FAIL")
    def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
