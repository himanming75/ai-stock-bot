from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.lifecycle_monitor import LifecycleSnapshot
from autonomous_paper_runtime.terminal_transition_gate import (
    ContinuedActualOrderMonitorTerminalTransitionGate,
)


def snap(seq, status="ACCEPTED", filled="0", position="0"):
    qty = Decimal("1")
    filled_d = Decimal(filled)
    return LifecycleSnapshot(
        sequence=seq,
        observed_at=f"2026-08-02T00:00:0{seq}+00:00",
        broker_order_id="broker-1",
        client_order_id="single-legacy",
        symbol="AAPL",
        side="BUY",
        status=status,
        quantity=qty,
        filled_quantity=filled_d,
        remaining_quantity=max(Decimal("0"), qty-filled_d),
        average_fill_price=Decimal("50") if filled_d else Decimal("0"),
        position_quantity=Decimal(position),
        position_average_price=Decimal("50") if Decimal(position) else Decimal("0"),
        cash=Decimal("99950") if filled_d else Decimal("100000"),
        equity=Decimal("100000"),
    )


class T(unittest.TestCase):
    def run_gate(self, values):
        with tempfile.TemporaryDirectory() as temp:
            gate = ContinuedActualOrderMonitorTerminalTransitionGate(
                lifecycle_ledger_path=Path(temp)/"life.jsonl",
                completion_ledger_path=Path(temp)/"complete.jsonl",
            )
            return gate.run(
                poller=lambda n: values[n-1],
                max_polls=len(values),
                network_requests_per_poll=3,
            )

    def test_active_stays_locked(self):
        r=self.run_gate([snap(1),snap(2),snap(3)])
        self.assertFalse(r.terminal_transition_observed)
        self.assertFalse(r.new_order_allowed)
        self.assertEqual(r.completion_report.state.value,"LOCKED_ACTIVE_ORDER")

    def test_partial_stays_locked(self):
        r=self.run_gate([snap(1),snap(2,"PARTIALLY_FILLED",".4",".4")])
        self.assertFalse(r.new_order_allowed)
        self.assertEqual(r.completion_report.state.value,"LOCKED_PARTIAL_FILL")

    def test_filled_unlocks(self):
        r=self.run_gate([snap(1),snap(2,"FILLED","1","1")])
        self.assertTrue(r.terminal_transition_observed)
        self.assertTrue(r.new_order_allowed)
        self.assertEqual(r.completion_report.state.value,"UNLOCKED_FILLED")

    def test_canceled_unlocks(self):
        r=self.run_gate([snap(1),snap(2,"CANCELED","0","0")])
        self.assertTrue(r.new_order_allowed)

    def test_rejected_unlocks(self):
        r=self.run_gate([snap(1),snap(2,"REJECTED","0","0")])
        self.assertTrue(r.new_order_allowed)

    def test_expired_unlocks(self):
        r=self.run_gate([snap(1),snap(2,"EXPIRED","0","0")])
        self.assertTrue(r.new_order_allowed)

    def test_unknown_safe_mode(self):
        r=self.run_gate([snap(1,"MYSTERY")])
        self.assertTrue(r.safe_mode_engaged)
        self.assertFalse(r.new_order_allowed)

    def test_invalid_filled_safe_mode(self):
        r=self.run_gate([snap(1,"FILLED",".5",".5")])
        self.assertTrue(r.safe_mode_engaged)

    def test_network_accounting(self):
        r=self.run_gate([snap(1),snap(2)])
        self.assertEqual(r.monitor_report.network_requests_executed,6)
        self.assertEqual(r.completion_report.write_requests_executed,0)

    def test_completion_ledger_written_only_terminal(self):
        r=self.run_gate([snap(1),snap(2,"FILLED","1","1")])
        self.assertTrue(r.completion_report.ledger_entry_written)

    def test_active_no_completion_ledger(self):
        r=self.run_gate([snap(1)])
        self.assertFalse(r.completion_report.ledger_entry_written)

    def test_json(self):
        r=self.run_gate([snap(1)])
        raw=r.to_json_dict()
        self.assertFalse(raw["new_order_allowed"])
        self.assertIn("monitor_report",raw)


if __name__=="__main__":
    unittest.main()
