import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.crash_recovery_restart_continuation_v83_61_64 import (
    run_crash_recovery_restart_continuation,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class CrashRecoveryRestartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = {
            name: self.root / f"{name}.json"
            for name in [
                "orchestrator", "cycle_lock", "dispatcher_lock",
                "runner_lock", "retry_lock", "approval_lock",
                "policy", "recovery_lock", "plan", "snapshot",
                "dashboard", "result",
            ]
        }
        self.ledger = self.root / "ledger.jsonl"
        write_json(self.paths["policy"], {
            "paper_only": True,
            "stale_lock_after_seconds": 1800,
            "automatic_resume_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_stage(self, **kwargs):
        return run_crash_recovery_restart_continuation(
            orchestrator_result_path=self.paths["orchestrator"],
            cycle_lock_path=self.paths["cycle_lock"],
            dispatcher_lock_path=self.paths["dispatcher_lock"],
            runner_lock_path=self.paths["runner_lock"],
            retry_lock_path=self.paths["retry_lock"],
            approval_lock_path=self.paths["approval_lock"],
            policy_path=self.paths["policy"],
            recovery_lock_path=self.paths["recovery_lock"],
            recovery_plan_path=self.paths["plan"],
            recovery_snapshot_path=self.paths["snapshot"],
            recovery_ledger_path=self.ledger,
            dashboard_path=self.paths["dashboard"],
            result_path=self.paths["result"],
            observed_at_override="2026-08-03T22:00:00+00:00",
            **kwargs,
        )

    def test_idle_passes(self):
        result = self.run_stage()
        self.assertEqual(result["state"], "RESTART_RECOVERY_IDLE")

    def test_resume_decision(self):
        write_json(self.paths["orchestrator"], {
            "state": "FULL_CYCLE_OBSERVING",
        })
        write_json(self.paths["cycle_lock"], {
            "active": True,
            "cycle_id": "cycle-1",
            "started_at": "2026-08-03T21:50:00+00:00",
        })
        result = self.run_stage(analyze=True)
        self.assertEqual(
            result["state"],
            "RESTART_RECOVERY_RESUME_READY",
        )

    def test_stale_lock_detected(self):
        write_json(self.paths["cycle_lock"], {
            "active": True,
            "cycle_id": "cycle-1",
            "started_at": "2026-08-03T20:00:00+00:00",
        })
        result = self.run_stage(analyze=True)
        self.assertEqual(
            result["state"],
            "RESTART_RECOVERY_STALE_LOCKS_FOUND",
        )

    def test_apply_abort(self):
        write_json(self.paths["orchestrator"], {
            "state": "FULL_CYCLE_WAIT_SCHEDULE",
        })
        write_json(self.paths["cycle_lock"], {
            "active": True,
            "cycle_id": "cycle-1",
            "started_at": "2026-08-03T21:50:00+00:00",
        })
        result = self.run_stage(
            analyze=True,
            apply_recovery=True,
        )
        self.assertEqual(
            result["state"],
            "RESTART_RECOVERY_ABORT_APPLIED",
        )

    def test_duplicate_recovery_blocked(self):
        write_json(self.paths["recovery_lock"], {
            "active": True,
            "recovery_id": "existing",
        })
        result = self.run_stage(analyze=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_broker_policy_fail_closed(self):
        policy = json.loads(self.paths["policy"].read_text())
        policy["broker_write_enabled"] = True
        write_json(self.paths["policy"], policy)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
