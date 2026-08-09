from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/coordinate_two_week_paper_validation_v3_0.py").read_text(encoding="utf-8")

    def test_reuses_existing_gate(self):
        self.assertIn("certify_runtime_observation_gate_v2_9_4.py",self.t)
        self.assertIn("ensure_gate",self.t)

    def test_ten_trading_days(self):
        self.assertIn("REQUIRED_TRADING_DAYS=10",self.t)
        self.assertIn("MIN_SUCCESSFUL_HOOKS_PER_DAY=3",self.t)

    def test_does_not_start_before_gate(self):
        self.assertIn("successful_gate_hooks>=REQUIRED_GATE_HOOKS",self.t)
        self.assertIn("PASS_WAITING_FOR_RUNTIME_GATE",self.t)

    def test_no_duplicate_engine(self):
        self.assertIn('"duplicate_trading_engine_created":False',self.t)
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest(","place_order("):
            self.assertNotIn(bad,self.t)

    def test_no_auto_promotion(self):
        self.assertIn('"automatic_promotion":False',self.t)
        self.assertIn('"production_parameter_modified":False',self.t)

if __name__=="__main__":
    unittest.main()
