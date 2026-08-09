
from pathlib import Path
import importlib.util
import unittest

def load(path,name):
    spec = importlib.util.spec_from_file_location(name,path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load(Path("dashboard/performance_diagnostics_v3_11.py"),"v311")
        cls.analytics = Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def test_two_trades_insufficient(self):
        d = self.m.build_performance_diagnostics([
            {"pnl":1,"symbol":"AAPL","reason":"TIME_EXIT"},
            {"pnl":2,"symbol":"AAPL","reason":"TIME_EXIT"},
        ])
        self.assertEqual(d["status"],"INSUFFICIENT_SAMPLE")
        self.assertEqual(d["canonical_numeric_trade_count"],2)

    def test_api(self):
        self.assertIn('"performance_diagnostics": diagnostics',self.analytics)

    def test_ui(self):
        self.assertIn('id="diagnosticsSection"',self.html)
        self.assertIn("Canonical Performance Diagnostics / 정식 거래 성과 진단",self.html)

    def test_groups(self):
        d = self.m.build_performance_diagnostics([{"pnl":1,"symbol":"AAPL","reason":"TIME_EXIT"}])
        self.assertEqual(len(d["by_symbol"]),1)
        self.assertEqual(len(d["by_exit_reason"]),1)

    def test_read_only(self):
        combined = Path("dashboard/performance_diagnostics_v3_11.py").read_text(encoding="utf-8")+self.analytics+self.html
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest("):
            self.assertNotIn(bad,combined)

if __name__ == "__main__":
    unittest.main()
