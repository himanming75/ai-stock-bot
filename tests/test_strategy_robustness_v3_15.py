
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
        cls.m = load(Path("dashboard/strategy_robustness_v3_15.py"), "v315")
        cls.analytics = Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def test_no_losses_is_unobserved(self):
        stress = load(Path("dashboard/strategy_stress_test_v3_14.py"), "v314_loss")
        trades=[{"pnl":1.0,"qty":1.0,"entry_price":100.0,"exit_price":101.0}]
        result=self.m._loss_amplification_boundary(stress,trades)
        self.assertEqual(result["status"],"UNOBSERVED_NO_LOSING_TRADES")
        self.assertIsNone(result["boundary"])

    def test_friction_boundary_found(self):
        stress = load(Path("dashboard/strategy_stress_test_v3_14.py"), "v314_boundary")
        trades=[{"pnl":1.0,"qty":1.0,"entry_price":100.0,"exit_price":101.0}]
        result=self.m._friction_boundary(stress,trades)
        self.assertEqual(result["status"],"FOUND")
        self.assertGreater(result["boundary"],0)

    def test_original_trades_not_mutated(self):
        stress = load(Path("dashboard/strategy_stress_test_v3_14.py"), "v314_mutation")
        trade={"pnl":1.0,"qty":1.0,"entry_price":100.0,"exit_price":101.0}
        original=dict(trade)
        self.m._friction_boundary(stress,[trade])
        self.assertEqual(trade,original)

    def test_api_exposed(self):
        self.assertIn('"strategy_robustness": robustness',self.analytics)

    def test_ui_and_safety(self):
        self.assertIn('id="robustnessSection"',self.html)
        self.assertIn("Strategy Robustness & Failure Boundary / 전략 견고성 및 실패 경계",self.html)
        combined=Path("dashboard/strategy_robustness_v3_15.py").read_text(encoding="utf-8")+self.analytics+self.html
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest("):
            self.assertNotIn(bad,combined)

if __name__ == "__main__":
    unittest.main()
