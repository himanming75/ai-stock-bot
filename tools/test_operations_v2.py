from __future__ import annotations
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from operations_v2.config_audit import ConfigurationDiffAuditor
from operations_v2.data_quality import DataQualityAuditor
from operations_v2.replay import HistoricalReplaySimulator


class Tests(unittest.TestCase):
    def bars(self):
        rows = []
        price = Decimal("100")
        for index in range(30):
            close = price + Decimal("1")
            rows.append({
                "timestamp": f"t{index:02d}",
                "open": str(price),
                "high": str(close + Decimal("0.5")),
                "low": str(price - Decimal("0.5")),
                "close": str(close),
                "volume": "1000",
            })
            price = close
        return rows

    def test_data_quality_pass(self):
        result = DataQualityAuditor().audit_bars(
            symbol="AAPL",
            bars=self.bars(),
        )
        self.assertEqual(result["status"], "PASS")

    def test_duplicate_timestamp_detected(self):
        bars = self.bars()
        bars[1]["timestamp"] = bars[0]["timestamp"]
        result = DataQualityAuditor().audit_bars(
            symbol="AAPL",
            bars=bars,
        )
        self.assertEqual(result["status"], "FAIL")

    def test_replay_creates_no_orders(self):
        result = HistoricalReplaySimulator().replay(
            symbol="AAPL",
            bars=self.bars(),
            fast_window=5,
            slow_window=20,
        )
        self.assertFalse(result["actual_orders_created"])
        self.assertFalse(result["broker_write_used"])

    def test_protected_change_detected(self):
        result = ConfigurationDiffAuditor().compare(
            baseline={"broker_write_enabled": False},
            current={"broker_write_enabled": True},
            protected_keys={"broker_write_enabled"},
        )
        self.assertFalse(result["safe"])

    def test_unchanged_config_safe(self):
        result = ConfigurationDiffAuditor().compare(
            baseline={"x": 1},
            current={"x": 1},
            protected_keys=set(),
        )
        self.assertTrue(result["safe"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
