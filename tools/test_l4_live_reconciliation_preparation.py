from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from live_reconciliation.drift import (
    compare_cash,
    compare_order,
    compare_positions,
)
from live_reconciliation.fill_registry import (
    DuplicateLiveFillError,
    LiveFillRegistry,
)
from live_reconciliation.models import OrderState, PositionState
from live_reconciliation.recovery import build_manual_repair_plan


class Tests(unittest.TestCase):
    def test_order_match(self):
        actual = OrderState.from_dict({
            "id": "1",
            "client_order_id": "c1",
            "symbol": "SPY",
            "side": "buy",
            "status": "filled",
            "filled_qty": "1",
            "filled_avg_price": "500",
        })
        result = compare_order({
            "client_order_id": "c1",
            "symbol": "SPY",
            "side": "buy",
        }, actual)
        self.assertFalse(result["drift_detected"])

    def test_position_drift(self):
        expected = [PositionState.from_dict({
            "symbol": "SPY", "qty": "1",
            "avg_entry_price": "500", "market_value": "500",
        })]
        actual = [PositionState.from_dict({
            "symbol": "SPY", "qty": "2",
            "avg_entry_price": "500", "market_value": "1000",
        })]
        self.assertTrue(
            compare_positions(expected, actual)["drift_detected"]
        )

    def test_cash_tolerance(self):
        result = compare_cash(
            expected_cash=Decimal("100"),
            actual_cash=Decimal("100.01"),
            expected_buying_power=Decimal("100"),
            actual_buying_power=Decimal("100"),
        )
        self.assertFalse(result["drift_detected"])

    def test_duplicate_fill_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = LiveFillRegistry(
                Path(directory) / "fills.json"
            )
            registry.reserve("fill-1")
            with self.assertRaises(DuplicateLiveFillError):
                registry.reserve("fill-1")

    def test_manual_repair_only(self):
        result = build_manual_repair_plan(["position"])
        self.assertFalse(result["automatic_repair_enabled"])
        self.assertFalse(result["automatic_order_replay_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
