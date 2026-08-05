from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_certification.service import (
    AutonomousPaperCertificationService,
)


class Tests(unittest.TestCase):
    def setup_repo(self, root: Path, cycles=60):
        paths = [
            "release/paper_automation_controller/actual",
            "release/automation_watchdog_restart_recovery/actual",
            "release/daily_session_manager_startup_autorun/actual",
            "release/v331_340_realtime_risk_monitoring/actual",
            "release/v351_360_system_health_monitoring/actual",
            "release/v371_380_autonomous_paper_operations_gate/actual",
            "release/v381_390_gate_remediation_readiness/actual",
        ]
        for item in paths:
            (root / item).mkdir(parents=True, exist_ok=True)

        controller_root = (
            root / "release/paper_automation_controller/actual"
        )
        (controller_root / "controller_summary.json").write_text(
            json.dumps({"status": "PASS"}),
            encoding="utf-8",
        )
        (controller_root / "checkpoint.json").write_text(
            json.dumps({"cycle_number": cycles}),
            encoding="utf-8",
        )
        rows = []
        for number in range(1, cycles + 1):
            rows.append(
                {
                    "cycle_number": number,
                    "errors": [],
                    "market_is_open": True,
                    "actual_broker_write_performed": False,
                    "actual_paper_orders_submitted": 0,
                    "actual_live_orders_submitted": 0,
                }
            )
        (controller_root / "controller_cycle_ledger.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n",
            encoding="utf-8",
        )

        fixtures = {
            "release/automation_watchdog_restart_recovery/actual/"
            "watchdog_summary.json": {
                "status": "PASS",
                "stop_reason": "CONTROLLER_COMPLETED",
            },
            "release/daily_session_manager_startup_autorun/actual/"
            "daily_session_summary.json": {"status": "PASS"},
            "release/v331_340_realtime_risk_monitoring/actual/"
            "risk_monitor_latest.json": {"risk_level": "NORMAL"},
            "release/v351_360_system_health_monitoring/actual/"
            "system_health_latest.json": {"status": "PASS"},
            "release/v371_380_autonomous_paper_operations_gate/actual/"
            "autonomous_gate_latest.json": {
                "status": "BLOCKED",
                "autonomous_paper_operations_allowed": False,
            },
            "release/v381_390_gate_remediation_readiness/actual/"
            "readiness_certificate.json": {
                "status": "CONDITIONAL_READINESS_CERTIFICATE",
            },
        }
        for relative, payload in fixtures.items():
            (root / relative).write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

        policy = root / "policy.json"
        policy.write_text(
            json.dumps({"minimum_controller_cycles": 60}),
            encoding="utf-8",
        )
        return policy

    def test_conditional_when_market_close_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            result = AutonomousPaperCertificationService().evaluate(
                repository_root=root,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["status"],
                "CONDITIONAL_CERTIFICATION",
            )
            self.assertIn(
                "MARKET_CLOSE_AUTO_STOP_OBSERVED",
                result["pending_market_evidence"],
            )

    def test_insufficient_cycles_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root, cycles=10)
            result = AutonomousPaperCertificationService().evaluate(
                repository_root=root,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "NOT_CERTIFIED")
            self.assertIn(
                "MINIMUM_CONTROLLER_CYCLES",
                result["failed_required_checks"],
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            result = AutonomousPaperCertificationService().evaluate(
                repository_root=root,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["evidence"][
                    "paper_orders_during_certification"
                ],
                0,
            )
            self.assertFalse(
                result["paper_order_submission_enabled"]
            )

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            out = root / "out"
            AutonomousPaperCertificationService().evaluate(
                repository_root=root,
                policy_path=policy,
                output_dir=out,
            )
            self.assertTrue(
                (out / "autonomous_paper_certificate.json").exists()
            )
            self.assertTrue(
                (
                    out
                    / "autonomous_paper_certificate_ledger.jsonl"
                ).exists()
            )

    def test_read_only_contract(self):
        source = inspect.getsource(
            AutonomousPaperCertificationService
        )
        self.assertIn(
            '"paper_order_submission_enabled": False',
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
