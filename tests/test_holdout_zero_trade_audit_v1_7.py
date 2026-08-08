from pathlib import Path
import unittest

class V17StaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path("tools/audit_holdout_zero_trade_v1_7.py").read_text(encoding="utf-8")

    def test_reuses_existing_shadow_module(self):
        self.assertIn("build_real_market_multitimeframe_shadow as shadow", self.text)
        self.assertIn("shadow.load_real_rows", self.text)
        self.assertIn("shadow.analyze_at_rows", self.text)
        self.assertIn("shadow.rolling_lifecycle", self.text)

    def test_requested_zero_trade_range_defaults(self):
        self.assertIn('default="2026-06-09"', self.text)
        self.assertIn('default="2026-07-07"', self.text)

    def test_root_cause_dimensions_present(self):
        for token in (
            "DATA_OR_FEATURE_COVERAGE",
            "HOLD_ONLY",
            "CONFIDENCE_FILTER",
            "REWARD_RISK_FILTER",
            "SELL_SELECTED_NO_LONG_ENTRY",
            "BUY_SIGNAL_LIFECYCLE_ENTRY_GAP",
        ):
            self.assertIn(token, self.text)

    def test_no_broker_submission_client_added(self):
        for forbidden in ("TradingClient(", "submit_order(", "place_order(", "order_submit"):
            self.assertNotIn(forbidden, self.text)

    def test_production_safety_contract(self):
        self.assertIn('"paper_runtime_modified": False', self.text)
        self.assertIn('"production_parameter_modified": False', self.text)
        self.assertIn('"broker_write_performed": False', self.text)
        self.assertIn('"order_submission_performed": False', self.text)

if __name__ == "__main__":
    unittest.main()
