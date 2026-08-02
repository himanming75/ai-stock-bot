from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from autonomous_paper_runtime.terminal_commit_cycle_completion import (
    TerminalCommitCycleCompletion,
)


class Tests(unittest.TestCase):
    def terminal_result(self, status="FILLED"):
        return {
            "status": "PASS",
            "state": "TERMINAL_OBSERVED",
            "client_order_id": "client-001",
            "broker_order_id": "broker-001",
            "order_status": status,
            "order_quantity": 10,
            "filled_quantity": 10 if status == "FILLED" else 3,
            "remaining_quantity": 0 if status == "FILLED" else 7,
            "average_fill_price": 100.5,
            "terminal_observed": True,
            "terminal_commit_ready": True,
            "safe_mode_engaged": False,
        }

    def monitor_state(self, status="FILLED"):
        return {
            "client_order_id": "client-001",
            "broker_order_id": "broker-001",
            "status": status,
            "quantity": 10,
            "filled_quantity": 10 if status == "FILLED" else 3,
            "remaining_quantity": 0 if status == "FILLED" else 7,
            "average_fill_price": 100.5,
            "active_order_present": False,
            "terminal_observed": True,
        }

    def run_case(self, lifecycle, monitor=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        lifecycle_path = root / "lifecycle.json"
        monitor_path = root / "monitor.json"
        terminal_token = root / "terminal.json"
        completion_token = root / "completion.json"
        ledger = root / "ledger.jsonl"
        audit = root / "audit.json"
        result = root / "result.json"
        lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
        if monitor is not None:
            monitor_path.write_text(json.dumps(monitor), encoding="utf-8")
        report = TerminalCommitCycleCompletion().run(
            lifecycle_result_path=lifecycle_path,
            monitor_state_path=monitor_path,
            terminal_commit_token_path=terminal_token,
            cycle_completion_token_path=completion_token,
            completion_ledger_path=ledger,
            audit_snapshot_path=audit,
            result_path=result,
        )
        return report, terminal_token, completion_token, ledger, audit

    def test_waits_before_terminal(self):
        report, terminal, completion, ledger, audit = self.run_case({
            "status": "PASS",
            "state": "WAIT_ACCEPTANCE",
            "client_order_id": "",
            "broker_order_id": "",
            "order_status": "",
            "terminal_observed": False,
            "terminal_commit_ready": False,
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_TERMINAL")
        self.assertFalse(terminal.exists())
        self.assertFalse(completion.exists())
        self.assertFalse(ledger.exists())
        self.assertFalse(audit.exists())

    def test_filled_completes_cycle(self):
        report, terminal, completion, ledger, audit = self.run_case(
            self.terminal_result("FILLED"),
            self.monitor_state("FILLED"),
        )
        self.assertEqual(report.state, "CYCLE_COMPLETED")
        self.assertTrue(report.terminal_commit_verified)
        self.assertTrue(report.cycle_completed)
        self.assertTrue(report.next_cycle_handoff_ready)
        self.assertTrue(terminal.exists())
        self.assertTrue(completion.exists())
        self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)
        self.assertTrue(audit.exists())

    def test_canceled_completes_cycle(self):
        report, *_ = self.run_case(
            self.terminal_result("CANCELED"),
            self.monitor_state("CANCELED"),
        )
        self.assertEqual(report.state, "CYCLE_COMPLETED")

    def test_duplicate_completion_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lifecycle = root / "lifecycle.json"
            monitor = root / "monitor.json"
            terminal = root / "terminal.json"
            completion = root / "completion.json"
            ledger = root / "ledger.jsonl"
            audit = root / "audit.json"
            result = root / "result.json"
            lifecycle.write_text(json.dumps(self.terminal_result()), encoding="utf-8")
            monitor.write_text(json.dumps(self.monitor_state()), encoding="utf-8")
            runner = TerminalCommitCycleCompletion()
            first = runner.run(
                lifecycle_result_path=lifecycle,
                monitor_state_path=monitor,
                terminal_commit_token_path=terminal,
                cycle_completion_token_path=completion,
                completion_ledger_path=ledger,
                audit_snapshot_path=audit,
                result_path=result,
            )
            second = runner.run(
                lifecycle_result_path=lifecycle,
                monitor_state_path=monitor,
                terminal_commit_token_path=terminal,
                cycle_completion_token_path=completion,
                completion_ledger_path=ledger,
                audit_snapshot_path=audit,
                result_path=result,
            )
            self.assertTrue(first.completion_ledger_written)
            self.assertTrue(second.duplicate_completion)
            self.assertFalse(second.completion_ledger_written)
            self.assertTrue(second.next_cycle_handoff_ready)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_monitor_state_mismatch_blocks(self):
        monitor = self.monitor_state()
        monitor["broker_order_id"] = "different"
        report, *_ = self.run_case(self.terminal_result(), monitor)
        self.assertEqual(report.status, "BLOCKED")

    def test_invalid_terminal_status_blocks(self):
        lifecycle = self.terminal_result()
        lifecycle["order_status"] = "ACCEPTED"
        report, *_ = self.run_case(lifecycle, self.monitor_state())
        self.assertEqual(report.status, "BLOCKED")

    def test_missing_monitor_state_blocks(self):
        report, *_ = self.run_case(self.terminal_result())
        self.assertEqual(report.status, "BLOCKED")

    def test_commit_ready_without_terminal_blocks(self):
        lifecycle = self.terminal_result()
        lifecycle["terminal_observed"] = False
        report, *_ = self.run_case(lifecycle, self.monitor_state())
        self.assertEqual(report.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
