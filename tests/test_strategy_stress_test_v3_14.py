
from pathlib import Path
import importlib.util
import unittest

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load(Path("dashboard/strategy_stress_test_v3_14.py"), "v314")
        cls.analytics = Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def sample_trade(self, pnl=1.0):
        return {
            "pnl": pnl,
            "qty": 1.0,
            "entry_price": 100.0,
            "exit_price": 101.0,
            "symbol": "AAPL",
            "reason": "TIME_EXIT",
            "entry_time": "2026-08-07T16:00:00+00:00",
            "exit_time": "2026-08-07T16:30:00+00:00",
            "time": "2026-08-07T16:30:00+00:00",
        }

    def test_stress_reduces_winner(self):
        mild = [x for x in self.m.SCENARIOS if x["id"] == "MILD"][0]
        stressed = self.m._stress_trade(self.sample_trade(1.0), mild)
        self.assertLess(stressed["pnl"], 1.0)

    def test_severe_more_adverse_than_mild(self):
        mild = [x for x in self.m.SCENARIOS if x["id"] == "MILD"][0]
        severe = [x for x in self.m.SCENARIOS if x["id"] == "SEVERE"][0]
        trade = self.sample_trade(1.0)
        self.assertLess(
            self.m._stress_trade(trade, severe)["pnl"],
            self.m._stress_trade(trade, mild)["pnl"],
        )

    def test_original_trade_not_modified(self):
        trade = self.sample_trade(1.0)
        original = dict(trade)
        self.m._stress_trade(trade, self.m.SCENARIOS[-1])
        self.assertEqual(trade, original)

    def test_api_exposed(self):
        self.assertIn('"strategy_stress_test": stress_test', self.analytics)

    def test_ui_and_safety(self):
        self.assertIn('id="stressTestSection"', self.html)
        self.assertIn("Strategy Stress Test / 전략 스트레스 테스트", self.html)
        combined = (
            Path("dashboard/strategy_stress_test_v3_14.py").read_text(encoding="utf-8")
            + self.analytics
            + self.html
        )
        for bad in ("TradingClient(", "submit_order(", "MarketOrderRequest("):
            self.assertNotIn(bad, combined)

if __name__ == "__main__":
    unittest.main()
