import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from analytics.performance_analytics_pipeline_v77_61_65 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.rec=self.r/"rec.json"
        write_json(self.rec,{"stage":"V77.56","status":"PASS","symbol":"SPY","side":"SELL",
          "cash_before":9000.0,"portfolio_equity_after":10030.0,
          "position_market_value_after":700.0,"realized_pnl_before":0.0,"realized_pnl_after":30.0,
          "portfolio_reconciliation_sha256":"rec"})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o61=self.r/"o61";build_performance_analytics(self.rec,o61);perf=o61/"performance_analytics_v77_61.json"
        o62=self.r/"o62";build_return_attribution(perf,self.rec,o62);attr=o62/"return_attribution_ledger_v77_62.json"
        o63=self.r/"o63";build_risk_metrics(perf,o63);risk=o63/"risk_metrics_v77_63.json"
        o64=self.r/"o64";run_performance_safety_gate(perf,attr,risk,o64)
        o65=self.r/"o65";cert=issue_performance_certificate(
          o61/"performance_analytics_verification_v77_61.json",
          o62/"return_attribution_ledger_verification_v77_62.json",
          o63/"risk_metrics_verification_v77_63.json",
          o64/"performance_safety_gate_verification_v77_64.json",o65)
        return cert
    def test_full_chain(self):self.assertEqual(self.chain()["status"],"PASS")
    def test_performance_values(self):
        o=self.r/"o";d=build_performance_analytics(self.rec,o)
        self.assertEqual(d["trade_pnl"],30.0);self.assertEqual(d["win_rate"],1.0)
    def test_attribution_balances(self):
        o61=self.r/"o61";build_performance_analytics(self.rec,o61)
        d=build_return_attribution(o61/"performance_analytics_v77_61.json",self.rec,self.r/"o62")
        self.assertEqual(d["attribution_delta"],0.0)
    def test_risk_metrics_finite(self):
        o61=self.r/"o61";build_performance_analytics(self.rec,o61)
        d=build_risk_metrics(o61/"performance_analytics_v77_61.json",self.r/"o63")
        self.assertTrue(all(finite_number(v) for v in d["metrics"].values()))
    def test_invalid_equity_blocked(self):
        write_json(self.rec,{"stage":"V77.56","status":"PASS","symbol":"SPY","side":"SELL",
          "cash_before":0.0,"portfolio_equity_after":0.0,"position_market_value_after":0.0,
          "realized_pnl_before":0.0,"realized_pnl_after":0.0,"portfolio_reconciliation_sha256":"rec"})
        with self.assertRaises(PerformanceAnalyticsError):build_performance_analytics(self.rec,self.r/"o")
    def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
