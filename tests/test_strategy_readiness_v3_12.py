
from pathlib import Path
import importlib.util
import unittest

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load(Path("dashboard/strategy_readiness_v3_12.py"),"v312")
        cls.analytics=Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html=Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def test_two_trades_never_ready(self):
        payload={
            "historical":{
                "numeric_trade_count":2,"win_rate":1.0,"average_trade":1.0,
                "profit_factor":"INF","max_realized_drawdown":0,"net_realized_pnl":2,
            },
            "performance_diagnostics":{
                "status":"INSUFFICIENT_SAMPLE","loss_count":0,
                "streaks":{"max_consecutive_wins":2,"max_consecutive_losses":0},
                "by_symbol":[{"name":"AAPL"}],
                "by_exit_reason":[{"name":"TIME_EXIT"}],
                "by_date":[{"name":"2026-08-07","net_realized_pnl":2}],
            },
        }
        r=self.m.build_strategy_readiness(payload)
        self.assertEqual(r["status"],"NOT_READY")
        self.assertLessEqual(r["overall_score"],49.0)

    def test_contracts(self):
        r=self.m.build_strategy_readiness({"historical":{"numeric_trade_count":0},"performance_diagnostics":{}})
        self.assertTrue(r["contracts"]["advisory_only"])
        self.assertFalse(r["contracts"]["automatic_promotion"])
        self.assertFalse(r["contracts"]["live_approval"])

    def test_api_exposed(self):
        self.assertIn('"strategy_readiness": readiness',self.analytics)

    def test_ui(self):
        self.assertIn('id="readinessSection"',self.html)
        self.assertIn("Strategy Quality & Readiness / 전략 품질 및 준비도",self.html)

    def test_read_only(self):
        combined=Path("dashboard/strategy_readiness_v3_12.py").read_text(encoding="utf-8")+self.analytics+self.html
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest("):
            self.assertNotIn(bad,combined)

if __name__=="__main__":
    unittest.main()
