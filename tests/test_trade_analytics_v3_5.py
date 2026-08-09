from pathlib import Path
import unittest


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = Path("dashboard/operations_dashboard_v3_2.py").read_text(encoding="utf-8")
        cls.analytics = Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def test_reuses_existing_dashboard(self):
        self.assertIn("ai_stock_bot_trade_analytics_v3_5", self.server)
        self.assertIn('root / "dashboard" / "trade_analytics_v3_5.py"', self.server)

    def test_metrics(self):
        for value in ("win_rate", "profit_factor", "average_win", "average_loss", "max_realized_drawdown", "by_symbol", "by_exit_reason"):
            self.assertIn(value, self.analytics)

    def test_validation_split(self):
        self.assertIn("WAITING_FOR_VALIDATION_START", self.analytics)
        self.assertIn("validation_start", self.analytics)

    def test_ui(self):
        for value in ('id="analyticsTradeCount"', 'id="analyticsCumulativeChart"', 'id="analyticsSymbolRows"', 'id="analyticsReasonRows"'):
            self.assertIn(value, self.html)

    def test_read_only(self):
        combined = self.server + self.analytics
        for bad in ("TradingClient(", "submit_order(", "place_order(", "MarketOrderRequest("):
            self.assertNotIn(bad, combined)


if __name__ == "__main__":
    unittest.main()
