from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.lifecycle_monitor import (
    ExistingPaperOrderLifecycleMonitor,
    LifecycleLedger,
    LifecycleSnapshot,
    MonitorDecision,
    build_snapshot,
)


def snapshot(
    sequence: int,
    *,
    status: str = "ACCEPTED",
    quantity: str = "1",
    filled: str = "0",
    position: str = "0",
    cash: str = "100000",
    equity: str = "100000",
) -> LifecycleSnapshot:
    return LifecycleSnapshot(
        sequence=sequence,
        observed_at=f"2026-08-01T20:00:0{sequence}+00:00",
        broker_order_id="broker-1",
        client_order_id="single-legacy",
        symbol="AAPL",
        side="BUY",
        status=status,
        quantity=Decimal(quantity),
        filled_quantity=Decimal(filled),
        remaining_quantity=max(
            Decimal("0"), Decimal(quantity) - Decimal(filled)
        ),
        average_fill_price=Decimal("50") if Decimal(filled) else Decimal("0"),
        position_quantity=Decimal(position),
        position_average_price=Decimal("50") if Decimal(position) else Decimal("0"),
        cash=Decimal(cash),
        equity=Decimal(equity),
    )


class LifecycleMonitorTests(unittest.TestCase):
    def monitor(self, values, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            ledger = LifecycleLedger(Path(temp) / "ledger.jsonl")
            monitor = ExistingPaperOrderLifecycleMonitor(ledger=ledger)
            result = monitor.monitor(
                poller=lambda sequence: values[sequence - 1],
                max_polls=len(values),
                **kwargs,
            )
            ledger_records = ledger.read_all()
        return result, ledger_records

    def test_active_continues_tracking(self):
        result, records = self.monitor([
            snapshot(1),
            snapshot(2),
            snapshot(3),
        ])
        self.assertEqual(result.decision, MonitorDecision.CONTINUE_TRACKING)
        self.assertEqual(result.poll_count, 3)
        self.assertFalse(result.new_order_allowed)
        self.assertEqual(len(records), 3)

    def test_active_to_partial_transition(self):
        result, _ = self.monitor([
            snapshot(1),
            snapshot(2, status="PARTIALLY_FILLED", filled=".4", position=".4", cash="99980"),
        ])
        self.assertEqual(
            result.decision, MonitorDecision.PARTIAL_FILL_TRACKING
        )
        self.assertEqual(result.material_transition_count, 1)
        self.assertEqual(
            result.transitions[0].filled_quantity_delta,
            Decimal(".4"),
        )

    def test_active_to_filled_stops(self):
        result, _ = self.monitor([
            snapshot(1),
            snapshot(2, status="FILLED", filled="1", position="1", cash="99950"),
            snapshot(3),
        ])
        self.assertEqual(result.decision, MonitorDecision.FILLED_COMPLETE)
        self.assertEqual(result.poll_count, 2)
        self.assertTrue(result.terminal)
        self.assertTrue(result.new_order_allowed)

    def test_terminal_canceled_stops(self):
        result, _ = self.monitor([
            snapshot(1),
            snapshot(2, status="CANCELED"),
        ])
        self.assertEqual(result.decision, MonitorDecision.TERMINAL_COMPLETE)
        self.assertTrue(result.new_order_allowed)

    def test_unknown_status_safe_mode(self):
        result, _ = self.monitor([snapshot(1, status="MYSTERY")])
        self.assertEqual(result.decision, MonitorDecision.SAFE_MODE)
        self.assertTrue(result.safe_mode_engaged)

    def test_invalid_partial_safe_mode(self):
        result, _ = self.monitor([
            snapshot(1, status="PARTIALLY_FILLED", filled="0")
        ])
        self.assertEqual(result.decision, MonitorDecision.SAFE_MODE)

    def test_invalid_filled_safe_mode(self):
        result, _ = self.monitor([
            snapshot(1, status="FILLED", filled=".5")
        ])
        self.assertTrue(result.safe_mode_engaged)
        self.assertFalse(result.new_order_allowed)

    def test_stop_on_material_transition(self):
        result, _ = self.monitor(
            [
                snapshot(1),
                snapshot(2, cash="99999"),
                snapshot(3),
            ],
            stop_on_material_transition=True,
        )
        self.assertEqual(result.poll_count, 2)

    def test_network_count(self):
        result, _ = self.monitor(
            [snapshot(1), snapshot(2)],
            network_requests_per_poll=3,
        )
        self.assertEqual(result.network_requests_executed, 6)
        self.assertEqual(result.write_requests_executed, 0)

    def test_sequence_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            monitor = ExistingPaperOrderLifecycleMonitor(
                ledger=LifecycleLedger(Path(temp) / "ledger.jsonl")
            )
            with self.assertRaises(ValueError):
                monitor.monitor(
                    poller=lambda sequence: snapshot(99),
                    max_polls=1,
                )

    def test_max_polls_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            monitor = ExistingPaperOrderLifecycleMonitor(
                ledger=LifecycleLedger(Path(temp) / "ledger.jsonl")
            )
            with self.assertRaises(ValueError):
                monitor.monitor(
                    poller=lambda sequence: snapshot(sequence),
                    max_polls=0,
                )

    def test_build_snapshot(self):
        item = build_snapshot(
            sequence=1,
            observed_at="now",
            order={
                "id": "broker-1",
                "client_order_id": "client-1",
                "symbol": "AAPL",
                "side": "buy",
                "status": "filled",
                "quantity": "1",
                "filled_quantity": "1",
                "average_fill_price": "50",
            },
            positions=[{
                "symbol": "AAPL",
                "quantity": "1",
                "average_entry_price": "50",
            }],
            account={"cash": "99950", "equity": "100000"},
        )
        self.assertEqual(item.remaining_quantity, Decimal("0"))
        self.assertEqual(item.position_quantity, Decimal("1"))

    def test_json(self):
        result, _ = self.monitor([snapshot(1)])
        raw = result.to_json_dict()
        self.assertEqual(raw["decision"], "CONTINUE_TRACKING")
        self.assertEqual(raw["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
