from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.lifecycle_monitor import LifecycleSnapshot
from autonomous_paper_runtime.terminal_monitor_commit_orchestrator import (
    TerminalMonitorCommitOrchestrator,
)


def snap(seq, status="ACCEPTED", filled="0", position="0"):
    quantity = Decimal("1")
    filled_q = Decimal(filled)
    return LifecycleSnapshot(
        sequence=seq,
        observed_at=f"2026-08-02T04:00:0{seq}+00:00",
        broker_order_id="broker-1",
        client_order_id="single-legacy",
        symbol="AAPL",
        side="BUY",
        status=status,
        quantity=quantity,
        filled_quantity=filled_q,
        remaining_quantity=max(Decimal("0"), quantity-filled_q),
        average_fill_price=Decimal("50") if filled_q else Decimal("0"),
        position_quantity=Decimal(position),
        position_average_price=Decimal("50") if Decimal(position) else Decimal("0"),
        cash=Decimal("99950") if filled_q else Decimal("100000"),
        equity=Decimal("100000"),
    )


class T(unittest.TestCase):
    def run_orchestrator(self, values):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            o=TerminalMonitorCommitOrchestrator(
                lifecycle_ledger_path=base/"lifecycle.jsonl",
                completion_ledger_path=base/"completion.jsonl",
                audit_ledger_path=base/"audit.jsonl",
                unlock_ledger_path=base/"unlock.jsonl",
                recovery_snapshot_path=base/"recovery.json",
            )
            report=o.run(
                poller=lambda n:values[n-1],
                max_polls=len(values),
                network_requests_per_poll=3,
                source_result_path="source.json",
            )
            files={
                "completion":(base/"completion.jsonl").exists(),
                "audit":(base/"audit.jsonl").exists(),
                "unlock":(base/"unlock.jsonl").exists(),
                "recovery":(base/"recovery.json").exists(),
            }
        return report,files

    def test_active_continue_no_commit(self):
        r,f=self.run_orchestrator([snap(1),snap(2),snap(3)])
        self.assertFalse(r.terminal_observed)
        self.assertFalse(r.commit_attempted)
        self.assertFalse(r.terminal_committed)
        self.assertFalse(r.next_order_allowed)
        self.assertFalse(any(f.values()))

    def test_partial_continue_no_commit(self):
        r,_=self.run_orchestrator([snap(1),snap(2,"PARTIALLY_FILLED",".4",".4")])
        self.assertFalse(r.terminal_observed)
        self.assertEqual(r.commit_report.state.value,"CONTINUE_TRACKING")

    def test_filled_commits(self):
        r,f=self.run_orchestrator([snap(1),snap(2,"FILLED","1","1")])
        self.assertTrue(r.terminal_observed)
        self.assertTrue(r.commit_attempted)
        self.assertTrue(r.terminal_committed)
        self.assertTrue(r.next_order_allowed)
        self.assertTrue(all(f.values()))
        self.assertEqual(r.commit_report.state.value,"COMMITTED_FILLED")

    def test_canceled_commits(self):
        r,_=self.run_orchestrator([snap(1),snap(2,"CANCELED","0","0")])
        self.assertTrue(r.terminal_committed)
        self.assertEqual(r.commit_report.state.value,"COMMITTED_TERMINAL_NO_FILL")

    def test_rejected_commits(self):
        r,_=self.run_orchestrator([snap(1),snap(2,"REJECTED","0","0")])
        self.assertTrue(r.next_order_allowed)

    def test_expired_commits(self):
        r,_=self.run_orchestrator([snap(1),snap(2,"EXPIRED","0","0")])
        self.assertTrue(r.next_order_allowed)

    def test_invalid_filled_safe_mode(self):
        r,_=self.run_orchestrator([snap(1,"FILLED",".5",".5")])
        self.assertTrue(r.safe_mode_engaged)
        self.assertFalse(r.next_order_allowed)

    def test_unknown_safe_mode(self):
        r,_=self.run_orchestrator([snap(1,"MYSTERY","0","0")])
        self.assertTrue(r.safe_mode_engaged)

    def test_network_accounting(self):
        r,_=self.run_orchestrator([snap(1),snap(2)])
        self.assertEqual(r.monitor_report.network_requests_executed,6)
        self.assertEqual(r.commit_report.network_requests_executed,6)
        self.assertEqual(r.commit_report.write_requests_executed,0)

    def test_monitor_stops_at_terminal(self):
        r,_=self.run_orchestrator([
            snap(1),
            snap(2,"FILLED","1","1"),
            snap(3),
        ])
        self.assertEqual(r.monitor_report.poll_count,2)

    def test_json(self):
        r,_=self.run_orchestrator([snap(1)])
        raw=r.to_json_dict()
        self.assertIn("monitor_report",raw)
        self.assertIn("commit_report",raw)

    def test_live_and_paper_zero(self):
        r,_=self.run_orchestrator([snap(1)])
        self.assertEqual(r.commit_report.actual_paper_orders_submitted,0)
        self.assertEqual(r.commit_report.live_orders_submitted,0)


if __name__=="__main__":
    unittest.main()
