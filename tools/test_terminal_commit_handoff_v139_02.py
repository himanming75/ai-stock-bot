from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.terminal_commit_handoff import TerminalCommitHandoff


class Tests(unittest.TestCase):
    def run_case(self, source: dict, *, existing_token: dict | None = None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        monitor = root / "monitor.json"
        token = root / "token.json"
        ledger = root / "recovery.jsonl"
        result = root / "result.json"
        monitor.write_text(json.dumps(source), encoding="utf-8")
        if existing_token is not None:
            token.write_text(json.dumps(existing_token), encoding="utf-8")
        report = TerminalCommitHandoff().run(
            monitor_result_path=monitor,
            handoff_token_path=token,
            recovery_ledger_path=ledger,
            result_path=result,
        )
        return report, token, ledger

    def terminal_source(self):
        return {
            "status": "PASS",
            "stage": "V139.01",
            "state": "TERMINAL_OBSERVED",
            "final_order_status": "FILLED",
            "terminal_observed": True,
            "terminal_commit_verified": True,
            "next_order_allowed": True,
            "safe_mode_engaged": False,
            "observed_at": "2026-08-02T04:00:00+00:00",
            "source_cycle_result_path": "cycle.json",
            "source_readiness_path": "readiness.json",
        }

    def test_active_order_waits(self):
        source = {
            "status": "PASS",
            "stage": "V139.01",
            "state": "WAIT_ACTIVE_ORDER",
            "final_order_status": "ACCEPTED",
            "terminal_observed": False,
            "terminal_commit_verified": False,
            "next_order_allowed": False,
            "safe_mode_engaged": False,
        }
        report, token, ledger = self.run_case(source)
        self.assertEqual(report.state, "WAIT_TERMINAL_COMMIT")
        self.assertFalse(report.handoff_created)
        self.assertFalse(token.exists())
        self.assertFalse(ledger.exists())

    def test_verified_terminal_creates_handoff(self):
        report, token, ledger = self.run_case(self.terminal_source())
        self.assertEqual(report.state, "HANDOFF_READY")
        self.assertTrue(report.handoff_created)
        self.assertTrue(report.next_cycle_unlock_ready)
        self.assertTrue(token.exists())
        self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_duplicate_is_idempotent(self):
        source = self.terminal_source()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            monitor = root / "monitor.json"
            token = root / "token.json"
            ledger = root / "recovery.jsonl"
            result = root / "result.json"
            monitor.write_text(json.dumps(source), encoding="utf-8")
            runner = TerminalCommitHandoff()
            first = runner.run(
                monitor_result_path=monitor,
                handoff_token_path=token,
                recovery_ledger_path=ledger,
                result_path=result,
            )
            second = runner.run(
                monitor_result_path=monitor,
                handoff_token_path=token,
                recovery_ledger_path=ledger,
                result_path=result,
            )
            self.assertTrue(first.handoff_created)
            self.assertTrue(second.duplicate_handoff)
            self.assertFalse(second.handoff_created)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_commit_without_terminal_blocks(self):
        source = {
            "status": "PASS",
            "stage": "V139.01",
            "state": "WAIT_ACTIVE_ORDER",
            "final_order_status": "ACCEPTED",
            "terminal_observed": False,
            "terminal_commit_verified": True,
            "next_order_allowed": False,
            "safe_mode_engaged": False,
        }
        report, token, _ = self.run_case(source)
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)
        self.assertFalse(token.exists())

    def test_conflicting_token_blocks(self):
        report, _, _ = self.run_case(
            self.terminal_source(),
            existing_token={"handoff_id": "handoff-different"},
        )
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)
        self.assertFalse(report.next_cycle_unlock_ready)


if __name__ == "__main__":
    unittest.main()
