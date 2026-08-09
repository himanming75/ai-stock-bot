from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.py = Path("dashboard/operations_dashboard_v3_2.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def test_unified_sections(self):
        for text in (
            "Account Equity",
            "Current Positions",
            "Open / Recent Orders",
            "Historical Closed Trades",
            "Validation Closed Trades",
        ):
            self.assertIn(text, self.html)

    def test_validation_vs_historical_split(self):
        self.assertIn("validation_closed_trades", self.py)
        self.assertIn("historical_closed_trades", self.py)
        self.assertIn("validation_start_trading_date", self.py)

    def test_runtime_discovery_only(self):
        self.assertIn("runtime_candidates", self.py)
        self.assertIn("discover_account_positions_orders", self.py)

    def test_read_only(self):
        for bad in (
            "do_POST",
            "do_PUT",
            "do_DELETE",
            "TradingClient(",
            "submit_order(",
            "place_order(",
            "requests.",
            "httpx.",
        ):
            self.assertNotIn(bad, self.py)

    def test_same_local_port(self):
        self.assertIn('default="127.0.0.1"', self.py)
        self.assertIn("default=8765", self.py)

if __name__ == "__main__":
    unittest.main()
