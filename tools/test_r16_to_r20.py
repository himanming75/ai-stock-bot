from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from realtime_paper_ops.market_clock import MarketClock
from realtime_paper_ops.monitor import OrderLifecycleMonitor
from realtime_paper_ops.order_queue import SafeOrderQueue
from realtime_paper_ops.sync import AccountPositionSyncPreview


class Tests(unittest.TestCase):
    def test_market_clock_regular(self):
        result = MarketClock().evaluate(
            observed_at=datetime(
                2026, 8, 5, 15, 0, tzinfo=timezone.utc
            )
        )
        self.assertTrue(result["regular_market_open"])
        self.assertFalse(result["automatic_runtime_start_enabled"])

    def test_sync_preview_no_modification(self):
        result = AccountPositionSyncPreview().reconcile(
            local_account={"cash": "10", "equity": "10", "buying_power": "20"},
            broker_account_fixture={"cash": "10", "equity": "10", "buying_power": "20"},
            local_positions=[],
            broker_positions_fixture=[],
        )
        self.assertTrue(result["account_in_sync"])
        self.assertFalse(result["actual_local_state_modified"])

    def test_queue_dispatch_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = SafeOrderQueue(Path(directory) / "q.jsonl")
            order = queue.enqueue(routed_order={
                "candidate_id": "c",
                "account_id": "a",
                "symbol": "AAPL",
                "side": "buy",
                "order_type": "market",
                "time_in_force": "day",
                "routed_notional": "8",
                "route_allowed": True,
                "submit_allowed": False,
                "broker_mode": "paper",
            })
            self.assertFalse(order.dispatch_allowed)
            with self.assertRaises(RuntimeError):
                queue.dispatch(order.queue_id)

    def test_invalid_transition_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            monitor = OrderLifecycleMonitor(
                Path(directory) / "ledger.jsonl"
            )
            with self.assertRaises(ValueError):
                monitor.transition(
                    queue_id="q",
                    previous_state="QUEUED_PREVIEW",
                    new_state="COMPLETED_PREVIEW",
                    reason="bad",
                )

    def test_valid_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            monitor = OrderLifecycleMonitor(
                Path(directory) / "ledger.jsonl"
            )
            result = monitor.transition(
                queue_id="q",
                previous_state="QUEUED_PREVIEW",
                new_state="VALIDATED_PREVIEW",
                reason="ok",
            )
            self.assertFalse(result["actual_order_modified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
