from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.operational_stability_bundle import (
    OperationalStabilityBundle,
)

class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        integration = {
            "status": "PASS",
            "state": "PAPER_INTEGRATION_READY_SUBMISSION_DISABLED",
            "paper_integration_ready": True,
            "engine_id": "engine-001",
            "client_order_id": "engine-001",
            "safe_mode_engaged": False,
            "actual_external_network_used": False,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        }
        health = {
            "disk_free_mb": 10000,
            "minimum_disk_free_mb": 1024,
            "heartbeat_age_seconds": 10,
            "maximum_heartbeat_age_seconds": 300,
            "filesystem_writable": True,
            "system_clock_synchronized": True,
            "runtime_process_count": 1,
            "log_directory_writable": True,
        }
        retry = {
            "max_attempts": 3,
            "initial_backoff_seconds": 1,
            "maximum_backoff_seconds": 30,
            "rate_limit_enabled": True,
            "retry_write_without_lookup": False,
        }
        return integration, health, retry

    def run_case(self, values, precreate_lock=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        paths = {
            "integration": root/"integration.json",
            "health": root/"health.json",
            "retry": root/"retry.json",
            "audit": root/"audit.json",
            "lock": root/"lock.json",
            "ledger": root/"ledger.jsonl",
            "health_result": root/"health_result.json",
            "token": root/"token.json",
            "result": root/"result.json",
        }
        for name, value in zip(("integration", "health", "retry"), values):
            if value is not None:
                self.write(paths[name], value)
        if precreate_lock:
            self.write(paths["lock"], {"released": False})

        result = OperationalStabilityBundle().run(
            integration_result_path=paths["integration"],
            health_snapshot_path=paths["health"],
            retry_policy_path=paths["retry"],
            daily_audit_path=paths["audit"],
            process_lock_path=paths["lock"],
            integrity_ledger_path=paths["ledger"],
            health_result_path=paths["health_result"],
            stability_token_path=paths["token"],
            result_path=paths["result"],
        )
        return result, paths

    def test_wait_before_paper_integration(self):
        values = list(self.data())
        values[0] = {
            "status": "PASS",
            "state": "WAIT_AUTONOMOUS_ENGINE",
            "paper_integration_ready": False,
            "safe_mode_engaged": False,
        }
        result, _ = self.run_case(values)
        self.assertEqual(result["state"], "WAIT_PAPER_INTEGRATION")

    def test_operational_stability_ready(self):
        result, paths = self.run_case(self.data())
        self.assertEqual(result["state"], "PAPER_RUNTIME_STABILITY_READY")
        self.assertTrue(result["daily_audit_written"])
        self.assertTrue(result["ledger_integrity_verified"])
        self.assertTrue(paths["token"].exists())

    def test_stale_heartbeat_blocks(self):
        values = list(self.data())
        values[1] = dict(values[1])
        values[1]["heartbeat_age_seconds"] = 999
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_process_lock_blocks(self):
        result, _ = self.run_case(self.data(), precreate_lock=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_non_idempotent_retry_blocks(self):
        values = list(self.data())
        values[2] = dict(values[2])
        values[2]["retry_write_without_lookup"] = True
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            integration, health, retry = self.data()
            paths = {
                "integration": root/"integration.json",
                "health": root/"health.json",
                "retry": root/"retry.json",
                "audit": root/"audit.json",
                "lock": root/"lock.json",
                "ledger": root/"ledger.jsonl",
                "health_result": root/"health_result.json",
                "token": root/"token.json",
                "result": root/"result.json",
            }
            for name, value in (
                ("integration", integration),
                ("health", health),
                ("retry", retry),
            ):
                self.write(paths[name], value)

            runner = OperationalStabilityBundle()
            kwargs = dict(
                integration_result_path=paths["integration"],
                health_snapshot_path=paths["health"],
                retry_policy_path=paths["retry"],
                daily_audit_path=paths["audit"],
                process_lock_path=paths["lock"],
                integrity_ledger_path=paths["ledger"],
                health_result_path=paths["health_result"],
                stability_token_path=paths["token"],
                result_path=paths["result"],
            )
            first = runner.run(**kwargs)
            second = runner.run(**kwargs)
            self.assertTrue(first["operational_stability_ready"])
            self.assertTrue(second["duplicate_stability_token"])
            self.assertEqual(
                len(paths["ledger"].read_text(encoding="utf-8").splitlines()),
                1,
            )

if __name__ == "__main__":
    unittest.main()
