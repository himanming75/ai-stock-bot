
from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = Path("dashboard/operations_dashboard_v3_2.py").read_text(encoding="utf-8")
        cls.viz = Path("dashboard/visualization_v3_4.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def test_reuses_existing_status_builder(self):
        self.assertIn("def _build_status_v3_2(root: Path):", self.server)
        self.assertIn("from dashboard.visualization_v3_4 import build_visualization", self.server)

    def test_visualization_sections(self):
        for value in ('id="equityChart"', 'id="pnlChart"', 'id="allocationChart"', 'id="validationChart"'):
            self.assertIn(value, self.html)

    def test_no_external_chart_dependency(self):
        combined = (self.html + self.viz).lower()
        for value in ("chart.js", "plotly", "highcharts", "d3.js"):
            self.assertNotIn(value, combined)

    def test_read_only(self):
        combined = self.server + self.viz
        for bad in ("TradingClient(", "submit_order(", "place_order(", "MarketOrderRequest("):
            self.assertNotIn(bad, combined)

    def test_validation_and_allocation(self):
        self.assertIn("validation_slots", self.viz)
        self.assertIn("position_allocation", self.viz)

if __name__ == "__main__":
    unittest.main()
