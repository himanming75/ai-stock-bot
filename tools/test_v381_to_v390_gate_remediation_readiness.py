from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from gate_remediation_readiness.service import (
    GateRemediationReadinessService,
)


class Tests(unittest.TestCase):
    def setup_repo(self, root: Path):
        paths = [
            "release/v371_380_autonomous_paper_operations_gate/actual",
            "release/v351_360_system_health_monitoring/actual",
            "release/paper_automation_controller/actual",
            "release/automation_watchdog_restart_recovery/actual",
        ]
        for item in paths:
            (root / item).mkdir(parents=True, exist_ok=True)

        (root / "release/v371_380_autonomous_paper_operations_gate/"
         "actual/autonomous_gate_latest.json").write_text(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "blockers": [
                        "HEALTH_CRITICAL:DUPLICATE_CONTROLLER_ROOTS",
                        "HEALTH_WARNING:CONTROLLER_HEARTBEAT_STALE_OR_MISSING",
                        "AUTONOMOUS_SUBMISSION_HARD_DISABLED",
                    ],
                }
            ),
            encoding="utf-8",
        )
        (root / "release/v351_360_system_health_monitoring/"
         "actual/system_health_latest.json").write_text(
            json.dumps(
                {
                    "process_health": {
                        "processes": [
                            {
                                "ProcessId": 100,
                                "ParentProcessId": 1,
                                "CommandLine": (
                                    "run_paper_automation_controller.py"
                                ),
                            },
                            {
                                "ProcessId": 101,
                                "ParentProcessId": 100,
                                "CommandLine": (
                                    "run_paper_automation_controller.py"
                                ),
                            },
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / "release/paper_automation_controller/actual/"
         "controller_summary.json").write_text(
            json.dumps({"status": "PASS"}),
            encoding="utf-8",
        )
        (root / "release/paper_automation_controller/actual/"
         "checkpoint.json").write_text(
            json.dumps({"cycle_number": 24}),
            encoding="utf-8",
        )
        (root / "release/automation_watchdog_restart_recovery/actual/"
         "watchdog_state.json").write_text(
            json.dumps({"status": "PASS"}),
            encoding="utf-8",
        )
        policy = root / "policy.json"
        policy.write_text("{}", encoding="utf-8")
        return policy

    def test_parent_child_resolves_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            result = GateRemediationReadinessService().evaluate(
                repository_root=root,
                output_dir=root / "out",
                policy_path=policy,
            )
            self.assertIn(
                "HEALTH_CRITICAL:DUPLICATE_CONTROLLER_ROOTS",
                result["resolved_by_normalization"],
            )

    def test_watchdog_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            result = GateRemediationReadinessService().evaluate(
                repository_root=root,
                output_dir=root / "out",
                policy_path=policy,
            )
            self.assertEqual(
                result["derived_watchdog_summary"]["source"],
                "watchdog_state.json",
            )

    def test_submission_stays_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            result = GateRemediationReadinessService().evaluate(
                repository_root=root,
                output_dir=root / "out",
                policy_path=policy,
            )
            self.assertFalse(
                result["autonomous_paper_operations_allowed"]
            )
            self.assertFalse(
                result["paper_order_submission_enabled"]
            )

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            out = root / "out"
            GateRemediationReadinessService().evaluate(
                repository_root=root,
                output_dir=out,
                policy_path=policy,
            )
            self.assertTrue(
                (out / "readiness_certificate.json").exists()
            )
            self.assertTrue(
                (out / "derived_watchdog_summary.json").exists()
            )

    def test_read_only_contract(self):
        source = inspect.getsource(
            GateRemediationReadinessService
        )
        self.assertIn(
            '"actual_remediation_action_performed": False',
            source,
        )
        self.assertIn(
            '"actual_paper_orders_submitted": 0',
            source,
        )
        self.assertIn(
            '"runtime_files_modified": False',
            source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
