from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.final_validation_release_bundle import (
    FinalValidationReleaseBundle,
    REQUIRED_FAILURE_SCENARIOS,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        stability = {
            "status": "PASS",
            "state": "PAPER_RUNTIME_STABILITY_READY",
            "operational_stability_ready": True,
            "engine_id": "engine-001",
            "safe_mode_engaged": False,
        }
        token = {
            "engine_id": "engine-001",
            "operational_stability_ready": True,
        }
        multi_day = {
            "completed_trading_days": 20,
            "minimum_trading_days": 20,
            "duplicate_orders": 0,
            "live_orders": 0,
            "risk_violations": 0,
            "recovery_failures": 0,
            "ledger_mismatches": 0,
            "reconciliation_errors": 0,
            "unexpected_broker_writes": 0,
        }
        failure = {
            "scenarios": [
                {
                    "name": name,
                    "safe_mode_or_recovery_passed": True,
                    "duplicate_orders": 0,
                    "live_orders": 0,
                    "unexpected_writes": 0,
                }
                for name in sorted(REQUIRED_FAILURE_SCENARIOS)
            ]
        }
        deployment = {
            "install_script_ready": True,
            "rollback_ready": True,
            "emergency_stop_ready": True,
            "recovery_runbook_ready": True,
            "scheduler_setup_ready": True,
            "daily_report_ready": True,
            "secret_storage_safe": True,
            "live_endpoint_blocked": True,
        }
        return stability, token, multi_day, failure, deployment

    def run_case(self, values):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        names = ["stability", "token", "multi_day", "failure", "deployment"]
        paths = {name: root/f"{name}.json" for name in names}

        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        result = FinalValidationReleaseBundle().run(
            stability_result_path=paths["stability"],
            stability_token_path=paths["token"],
            multi_day_snapshot_path=paths["multi_day"],
            failure_injection_snapshot_path=paths["failure"],
            deployment_readiness_snapshot_path=paths["deployment"],
            validation_certificate_path=root/"validation.json",
            failure_certificate_path=root/"failure_certificate.json",
            release_manifest_path=root/"manifest.json",
            production_token_path=root/"production_token.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_wait_before_operational_stability(self):
        values = list(self.data())
        values[0] = {
            "status": "PASS",
            "state": "WAIT_PAPER_INTEGRATION",
            "operational_stability_ready": False,
            "safe_mode_engaged": False,
        }
        result, _ = self.run_case(values)
        self.assertEqual(result["state"], "WAIT_OPERATIONAL_STABILITY")

    def test_final_release_ready(self):
        result, root = self.run_case(self.data())
        self.assertEqual(result["state"], "PAPER_PRODUCTION_RELEASE_READY")
        self.assertTrue(result["paper_production_release_ready"])
        self.assertTrue((root/"production_token.json").exists())

    def test_insufficient_days_blocks(self):
        values = list(self.data())
        values[2] = dict(values[2])
        values[2]["completed_trading_days"] = 19
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_orders_blocks(self):
        values = list(self.data())
        values[2] = dict(values[2])
        values[2]["duplicate_orders"] = 1
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_missing_failure_scenario_blocks(self):
        values = list(self.data())
        values[3] = {
            "scenarios": values[3]["scenarios"][:-1]
        }
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_unsafe_secret_storage_blocks(self):
        values = list(self.data())
        values[4] = dict(values[4])
        values[4]["secret_storage_safe"] = False
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
