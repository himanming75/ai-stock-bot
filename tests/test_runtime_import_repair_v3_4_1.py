
from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = Path(
            "dashboard/operations_dashboard_v3_2.py"
        ).read_text(encoding="utf-8")

    def test_file_location_import_used(self):
        self.assertIn(
            "importlib.util.spec_from_file_location",
            self.server,
        )
        self.assertIn(
            'root / "dashboard" / "visualization_v3_4.py"',
            self.server,
        )

    def test_package_import_removed(self):
        self.assertNotIn(
            "from dashboard.visualization_v3_4 import build_visualization",
            self.server,
        )

    def test_visualization_status_preserved(self):
        self.assertIn(
            'payload["visualization_status"] = "PASS"',
            self.server,
        )
        self.assertIn(
            "ISOLATED_VISUALIZATION_ERROR",
            self.server,
        )

    def test_no_trading_write(self):
        for bad in (
            "TradingClient(",
            "submit_order(",
            "place_order(",
            "MarketOrderRequest(",
        ):
            self.assertNotIn(bad, self.server)

    def test_existing_server_preserved(self):
        self.assertIn(
            "class Handler(BaseHTTPRequestHandler):",
            self.server,
        )

if __name__ == "__main__":
    unittest.main()
