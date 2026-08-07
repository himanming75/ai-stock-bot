from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    def setUp(self):
        self.text = Path(
            "tools/build_real_market_multitimeframe_shadow.py"
        ).read_text(encoding="utf-8")

    def test_lifecycle_mode_present(self):
        self.assertIn("def rolling_lifecycle(", self.text)
        self.assertIn('choices=("snapshot","rolling","lifecycle")', self.text)

    def test_canonical_entry_contract(self):
        self.assertIn(
            '"sell_signal_contract": "DELEGATED_TO_POSITION_LIFECYCLE_NOT_SHORT_ENTRY"',
            self.text,
        )
        self.assertIn('if side == "SELL":', self.text)
        self.assertIn("SELL_DELEGATED_TO_POSITION_LIFECYCLE", self.text)

    def test_current_lifecycle_values(self):
        self.assertIn('"take_profit_pct": 0.008', self.text)
        self.assertIn('"stop_loss_pct": 0.005', self.text)
        self.assertIn('"max_hold_minutes": 30', self.text)
        self.assertIn('"market_close_buffer_minutes": 15', self.text)

    def test_interpretation_contract(self):
        self.assertIn('"production_paper_strategy_modified": False', self.text)
        self.assertIn('"exact_broker_fill_equivalence_asserted": False', self.text)
        self.assertIn('"parameter_optimization_performed": False', self.text)
        self.assertIn('"sell_signals_open_short_positions": False', self.text)

    def test_no_broker_write_added(self):
        self.assertNotIn("client.submit_order", self.text)
        self.assertNotIn("TradingClient(", self.text)

if __name__ == "__main__":
    unittest.main()
