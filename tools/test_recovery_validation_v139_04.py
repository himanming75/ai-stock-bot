from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.recovery_validation import RecoveryValidation


class Tests(unittest.TestCase):
    def ready_result(self):
        return {
            "status": "PASS",
            "state": "NEXT_CYCLE_UNLOCKED",
            "unlock_id": "unlock-001",
            "handoff_id": "handoff-001",
            "next_cycle_ready": True,
            "safe_mode_engaged": False,
        }

    def ready_token(self):
        return {
            "unlock_id": "unlock-001",
            "handoff_id": "handoff-001",
            "next_cycle_ready": True,
        }

    def ready_ledger(self):
        return [{
            "event": "NEXT_CYCLE_UNLOCK_CREATED",
            "unlock_id": "unlock-001",
            "handoff_id": "handoff-001",
        }]

    def ready_snapshot(self):
        return {
            "unlock_id": "unlock-001",
            "handoff_id": "handoff-001",
            "unlock_token_verified": True,
            "next_cycle_ready": True,
        }

    def run_case(self, result, token=None, ledger=None, snapshot=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        result_path = root / "unlock_result.json"
        token_path = root / "unlock_token.json"
        ledger_path = root / "unlock_ledger.jsonl"
        snapshot_path = root / "recovery.json"
        output_path = root / "result.json"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        if token is not None:
            token_path.write_text(json.dumps(token), encoding="utf-8")
        if ledger is not None:
            ledger_path.write_text(
                "\n".join(json.dumps(row) for row in ledger) + "\n",
                encoding="utf-8",
            )
        if snapshot is not None:
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        report = RecoveryValidation().run(
            unlock_result_path=result_path,
            unlock_token_path=token_path,
            unlock_ledger_path=ledger_path,
            recovery_snapshot_path=snapshot_path,
            result_path=output_path,
        )
        return report

    def test_waits_before_unlock(self):
        report = self.run_case({
            "status": "PASS",
            "state": "WAIT_HANDOFF",
            "unlock_id": "",
            "handoff_id": "",
            "next_cycle_ready": False,
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_UNLOCK")
        self.assertFalse(report.recovery_validated)

    def test_valid_recovery_passes(self):
        report = self.run_case(
            self.ready_result(),
            self.ready_token(),
            self.ready_ledger(),
            self.ready_snapshot(),
        )
        self.assertEqual(report.state, "RECOVERY_VALIDATED")
        self.assertTrue(report.recovery_validated)

    def test_missing_token_blocks(self):
        report = self.run_case(
            self.ready_result(),
            None,
            self.ready_ledger(),
            self.ready_snapshot(),
        )
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_duplicate_ledger_event_blocks(self):
        ledger = self.ready_ledger() * 2
        report = self.run_case(
            self.ready_result(),
            self.ready_token(),
            ledger,
            self.ready_snapshot(),
        )
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_snapshot_mismatch_blocks(self):
        snapshot = self.ready_snapshot()
        snapshot["unlock_id"] = "unlock-other"
        report = self.run_case(
            self.ready_result(),
            self.ready_token(),
            self.ready_ledger(),
            snapshot,
        )
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_token_mismatch_blocks(self):
        token = self.ready_token()
        token["handoff_id"] = "handoff-other"
        report = self.run_case(
            self.ready_result(),
            token,
            self.ready_ledger(),
            self.ready_snapshot(),
        )
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)


if __name__ == "__main__":
    unittest.main()
