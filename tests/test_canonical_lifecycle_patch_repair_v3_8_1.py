
from pathlib import Path
import unittest


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analytics = Path(
            "dashboard/trade_analytics_v3_5.py"
        ).read_text(encoding="utf-8")

    def test_canonical_module_integrated(self):
        self.assertIn(
            "ai_stock_bot_canonical_lifecycle_v3_8",
            self.analytics,
        )

    def test_canonical_source_priority(self):
        self.assertIn(
            "canonical_actual_round_trip",
            self.analytics,
        )
        self.assertIn(
            "runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl",
            self.analytics,
        )

    def test_discovery_exposed(self):
        self.assertIn(
            '"canonical_lifecycle_discovery": lifecycle_discovery',
            self.analytics,
        )

    def test_v37_reconstruction_retained(self):
        self.assertIn(
            "cross_ledger_trade_reconstruction_v3_7.py",
            self.analytics,
        )
        self.assertIn(
            '"cross_ledger_reconstruction": reconstruction_audit',
            self.analytics,
        )

    def test_read_only(self):
        for bad in (
            "TradingClient(",
            "submit_order(",
            "MarketOrderRequest(",
        ):
            self.assertNotIn(bad, self.analytics)


if __name__ == "__main__":
    unittest.main()
