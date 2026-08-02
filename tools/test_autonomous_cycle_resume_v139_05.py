from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from autonomous_paper_runtime.autonomous_cycle_resume import AutonomousCycleResume


class Tests(unittest.TestCase):
    def valid_source(self):
        return {
            "status": "PASS",
            "state": "RECOVERY_VALIDATED",
            "recovery_validated": True,
            "unlock_id": "unlock-001",
            "handoff_id": "handoff-001",
            "safe_mode_engaged": False,
        }

    def run_case(self, source, existing=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        src = root / "recovery.json"
        token = root / "token.json"
        ledger = root / "ledger.jsonl"
        snap = root / "snapshot.json"
        result = root / "result.json"
        src.write_text(json.dumps(source), encoding="utf-8")
        if existing is not None:
            token.write_text(json.dumps(existing), encoding="utf-8")
        report = AutonomousCycleResume().run(
            recovery_result_path=src,
            resume_token_path=token,
            cycle_ledger_path=ledger,
            recovery_snapshot_path=snap,
            result_path=result,
        )
        return report, token, ledger, snap

    def test_waits_before_recovery_validation(self):
        report, token, ledger, snap = self.run_case({
            "status": "PASS",
            "state": "WAIT_UNLOCK",
            "recovery_validated": False,
            "unlock_id": "",
            "handoff_id": "",
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_RECOVERY_VALIDATION")
        self.assertFalse(token.exists())
        self.assertFalse(ledger.exists())
        self.assertFalse(snap.exists())

    def test_valid_recovery_resumes_cycle(self):
        report, token, ledger, snap = self.run_case(self.valid_source())
        self.assertEqual(report.state, "CYCLE_RESUMED")
        self.assertTrue(report.cycle_created)
        self.assertTrue(report.next_order_eligibility_ready)
        self.assertTrue(token.exists())
        self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)
        self.assertTrue(snap.exists())

    def test_duplicate_resume_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            src = root / "recovery.json"
            token = root / "token.json"
            ledger = root / "ledger.jsonl"
            snap = root / "snapshot.json"
            result = root / "result.json"
            src.write_text(json.dumps(self.valid_source()), encoding="utf-8")
            runner = AutonomousCycleResume()
            first = runner.run(
                recovery_result_path=src, resume_token_path=token,
                cycle_ledger_path=ledger, recovery_snapshot_path=snap,
                result_path=result,
            )
            second = runner.run(
                recovery_result_path=src, resume_token_path=token,
                cycle_ledger_path=ledger, recovery_snapshot_path=snap,
                result_path=result,
            )
            self.assertTrue(first.cycle_created)
            self.assertTrue(second.duplicate_cycle)
            self.assertFalse(second.cycle_created)
            self.assertTrue(second.next_order_eligibility_ready)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_recovery_state_mismatch_blocks(self):
        source = self.valid_source()
        source["state"] = "WAIT_UNLOCK"
        report, *_ = self.run_case(source)
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_missing_identity_blocks(self):
        source = self.valid_source()
        source["unlock_id"] = ""
        report, *_ = self.run_case(source)
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_conflicting_resume_token_blocks(self):
        report, *_ = self.run_case(
            self.valid_source(),
            {"cycle_id": "cycle-other", "unlock_id": "unlock-other"},
        )
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)


if __name__ == "__main__":
    unittest.main()
