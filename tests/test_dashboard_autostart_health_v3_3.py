
from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")
        cls.health = Path("dashboard/health_snapshot_v3_3.py").read_text(encoding="utf-8")
        cls.start = Path("START_DASHBOARD_V3_3.ps1").read_text(encoding="utf-8")
        cls.install = Path("INSTALL_DASHBOARD_AUTOSTART_V3_3.ps1").read_text(encoding="utf-8")

    def test_alert_ui(self):
        self.assertIn('id="alertSummary"', self.html)
        self.assertIn("V3.3 Health Layer", self.html)

    def test_health_snapshot_reuses_v32(self):
        self.assertIn("from dashboard.operations_dashboard_v3_2 import build_status", self.health)

    def test_autostart_single_instance(self):
        self.assertIn("MultipleInstances IgnoreNew", self.install)
        self.assertIn("already running on port", self.start)

    def test_port_policy(self):
        self.assertIn("$Port=8766", self.start)
        self.assertIn("localhost:8766", self.install)

    def test_no_trading_write(self):
        combined = self.health + self.start + self.install
        for bad in ("TradingClient(", "submit_order(", "place_order(", "MarketOrderRequest("):
            self.assertNotIn(bad, combined)

if __name__ == "__main__":
    unittest.main()
