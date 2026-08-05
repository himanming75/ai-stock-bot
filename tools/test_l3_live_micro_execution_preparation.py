from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from live_execution.dry_run import LiveDryRunTransport
from live_execution.idempotency import (
    DuplicateLiveOrderError,
    LiveIdempotencyRegistry,
)
from live_execution.models import LiveMicroOrder
from live_execution.risk import authorize_micro_order
from live_execution.rollback import build_rollback_plan


class Tests(unittest.TestCase):
    def test_order_model(self):
        order = LiveMicroOrder(
            symbol="SPY",
            side="buy",
            order_type="market",
            time_in_force="day",
            notional=Decimal("1"),
            client_order_id="l3-test-1",
        )
        self.assertEqual(order.payload()["notional"], "1")

    def test_risk_limit(self):
        result = authorize_micro_order(
            estimated_notional=Decimal("11"),
            maximum_order_notional=Decimal("10"),
            daily_order_count=0,
            maximum_daily_orders=1,
            daily_realized_loss=Decimal("0"),
            maximum_daily_loss=Decimal("10"),
            symbol="SPY",
            allowed_symbols=("SPY",),
        )
        self.assertFalse(result["approved"])

    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = LiveIdempotencyRegistry(
                Path(directory) / "registry.json"
            )
            registry.reserve("abc")
            with self.assertRaises(DuplicateLiveOrderError):
                registry.reserve("abc")

    def test_dry_run_zero_network(self):
        result = LiveDryRunTransport().submit({"symbol": "SPY"})
        self.assertFalse(result["broker_network_used"])
        self.assertFalse(result["broker_submission_attempted"])

    def test_rollback_manual(self):
        result = build_rollback_plan(client_order_id="x")
        self.assertFalse(result["automatic_rollback_enabled"])
        self.assertFalse(result["automatic_order_replay_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
