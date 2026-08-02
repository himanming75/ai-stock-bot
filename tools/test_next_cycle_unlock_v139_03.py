from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.next_cycle_unlock import NextCycleUnlock


class Tests(unittest.TestCase):
    def ready_result(self):
        return {
            "status": "PASS",
            "state": "HANDOFF_READY",
            "handoff_id": "handoff-test-001",
            "next_cycle_unlock_ready": True,
            "safe_mode_engaged": False,
        }

    def ready_token(self):
        return {
            "handoff_id": "handoff-test-001",
            "terminal_observed": True,
            "terminal_commit_verified": True,
            "next_cycle_unlock_ready": True,
        }

    def run_case(self, result, token=None, existing_unlock=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        result_path = root / "handoff_result.json"
        token_path = root / "handoff_token.json"
        unlock_path = root / "unlock.json"
        ledger_path = root / "unlock.jsonl"
        recovery_path = root / "recovery.json"
        output_path = root / "result.json"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        if token is not None:
            token_path.write_text(json.dumps(token), encoding="utf-8")
        if existing_unlock is not None:
            unlock_path.write_text(json.dumps(existing_unlock), encoding="utf-8")
        report = NextCycleUnlock().run(
            handoff_result_path=result_path,
            handoff_token_path=token_path,
            unlock_token_path=unlock_path,
            unlock_ledger_path=ledger_path,
            recovery_snapshot_path=recovery_path,
            result_path=output_path,
        )
        return report, unlock_path, ledger_path, recovery_path

    def test_waits_before_handoff(self):
        report, unlock, ledger, recovery = self.run_case({
            "status": "PASS",
            "state": "WAIT_TERMINAL_COMMIT",
            "handoff_id": "",
            "next_cycle_unlock_ready": False,
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_HANDOFF")
        self.assertFalse(unlock.exists())
        self.assertFalse(ledger.exists())
        self.assertFalse(recovery.exists())

    def test_ready_handoff_creates_unlock(self):
        report, unlock, ledger, recovery = self.run_case(
            self.ready_result(), self.ready_token()
        )
        self.assertEqual(report.state, "NEXT_CYCLE_UNLOCKED")
        self.assertTrue(report.unlock_created)
        self.assertTrue(report.next_cycle_ready)
        self.assertTrue(unlock.exists())
        self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)
        self.assertTrue(recovery.exists())

    def test_duplicate_unlock_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            handoff_result = root / "handoff_result.json"
            handoff_token = root / "handoff_token.json"
            unlock = root / "unlock.json"
            ledger = root / "unlock.jsonl"
            recovery = root / "recovery.json"
            result = root / "result.json"
            handoff_result.write_text(json.dumps(self.ready_result()), encoding="utf-8")
            handoff_token.write_text(json.dumps(self.ready_token()), encoding="utf-8")
            runner = NextCycleUnlock()
            first = runner.run(
                handoff_result_path=handoff_result,
                handoff_token_path=handoff_token,
                unlock_token_path=unlock,
                unlock_ledger_path=ledger,
                recovery_snapshot_path=recovery,
                result_path=result,
            )
            second = runner.run(
                handoff_result_path=handoff_result,
                handoff_token_path=handoff_token,
                unlock_token_path=unlock,
                unlock_ledger_path=ledger,
                recovery_snapshot_path=recovery,
                result_path=result,
            )
            self.assertTrue(first.unlock_created)
            self.assertTrue(second.duplicate_unlock)
            self.assertFalse(second.unlock_created)
            self.assertTrue(second.next_cycle_ready)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_missing_required_token_blocks(self):
        report, _, _, _ = self.run_case(self.ready_result())
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_handoff_id_mismatch_blocks(self):
        token = self.ready_token()
        token["handoff_id"] = "handoff-other"
        report, _, _, _ = self.run_case(self.ready_result(), token)
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_conflicting_unlock_blocks(self):
        report, _, _, _ = self.run_case(
            self.ready_result(),
            self.ready_token(),
            {"unlock_id": "unlock-other", "handoff_id": "handoff-other"},
        )
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)


if __name__ == "__main__":
    unittest.main()
