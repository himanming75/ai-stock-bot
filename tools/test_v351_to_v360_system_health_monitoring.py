from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from system_health_monitoring.service import (
    SystemHealthMonitoringService,
)


class Tests(unittest.TestCase):
    def setup_repo(self, root: Path):
        paths = [
            "release/paper_automation_controller/actual",
            "release/automation_watchdog_restart_recovery/actual",
            "release/daily_session_manager_startup_autorun/actual",
            "release/actual_market_polling_validation/actual",
            "release/v321_330_realtime_portfolio_monitoring/actual",
            "release/v331_340_realtime_risk_monitoring/actual",
            "release/v341_350_performance_analytics/actual",
        ]
        for item in paths:
            (root / item).mkdir(parents=True, exist_ok=True)

        now = "2026-01-01T12:00:00+00:00"
        json_files = {
            "release/paper_automation_controller/actual/checkpoint.json": {
                "completed_at": now,
                "cycle_number": 10,
            },
            "release/paper_automation_controller/actual/controller_summary.json": {
                "status": "PASS",
                "market_is_open": True,
            },
            "release/automation_watchdog_restart_recovery/actual/watchdog_state.json": {
                "status": "PASS"
            },
            "release/automation_watchdog_restart_recovery/actual/watchdog_summary.json": {
                "status": "PASS"
            },
            "release/daily_session_manager_startup_autorun/actual/daily_session_state.json": {
                "status": "PASS"
            },
            "release/daily_session_manager_startup_autorun/actual/daily_session_summary.json": {
                "status": "PASS"
            },
            "release/v321_330_realtime_portfolio_monitoring/actual/portfolio_monitor_latest.json": {
                "status": "PASS"
            },
            "release/v331_340_realtime_risk_monitoring/actual/risk_monitor_latest.json": {
                "status": "PASS"
            },
            "release/v341_350_performance_analytics/actual/performance_analytics_latest.json": {
                "status": "PASS_WITH_WARNINGS"
            },
        }
        for relative, payload in json_files.items():
            (root / relative).write_text(
                json.dumps(payload), encoding="utf-8"
            )

        jsonl_files = [
            "release/paper_automation_controller/actual/controller_cycle_ledger.jsonl",
            "release/automation_watchdog_restart_recovery/actual/watchdog_ledger.jsonl",
            "release/daily_session_manager_startup_autorun/actual/daily_session_ledger.jsonl",
            "release/actual_market_polling_validation/actual/polling_ledger.jsonl",
        ]
        for relative in jsonl_files:
            (root / relative).write_text(
                json.dumps({"status": "PASS"}) + "\n",
                encoding="utf-8",
            )

        policy = root / "policy.json"
        policy.write_text(
            json.dumps(
                {
                    "heartbeat_warning_seconds": 120,
                    "stale_lock_warning_seconds": 120,
                    "disk_warning_percent": 99,
                    "disk_critical_percent": 100,
                    "jsonl_tail_validation_limit": 100,
                }
            ),
            encoding="utf-8",
        )
        return policy

    def service(self, processes=None):
        return SystemHealthMonitoringService(
            process_provider=lambda: processes or [],
            now_provider=lambda: datetime(
                2026, 1, 1, 12, 1, tzinfo=timezone.utc
            ),
        )

    def test_valid_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            result = self.service().evaluate(
                repository_root=root,
                output_dir=root / "out",
                policy_path=policy,
            )
            self.assertEqual(result["status"], "PASS")

    def test_invalid_jsonl_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            target = (
                root
                / "release/paper_automation_controller/actual/"
                "controller_cycle_ledger.jsonl"
            )
            target.write_text("{invalid\n", encoding="utf-8")
            result = self.service().evaluate(
                repository_root=root,
                output_dir=root / "out",
                policy_path=policy,
            )
            self.assertIn(
                "INVALID_JSONL_DETECTED",
                result["critical_issues"],
            )

    def test_duplicate_root_detection(self):
        processes = [
            {
                "ProcessId": 100,
                "ParentProcessId": 1,
                "CommandLine": "run_paper_automation_controller.py",
            },
            {
                "ProcessId": 200,
                "ParentProcessId": 1,
                "CommandLine": "run_paper_automation_controller.py",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            result = self.service(processes).evaluate(
                repository_root=root,
                output_dir=root / "out",
                policy_path=policy,
            )
            self.assertIn(
                "DUPLICATE_CONTROLLER_ROOTS",
                result["critical_issues"],
            )

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.setup_repo(root)
            out = root / "out"
            self.service().evaluate(
                repository_root=root,
                output_dir=out,
                policy_path=policy,
            )
            self.assertTrue(
                (out / "system_health_dashboard.json").exists()
            )
            self.assertTrue(
                (out / "system_health_ledger.jsonl").exists()
            )

    def test_read_only_contract(self):
        source = inspect.getsource(SystemHealthMonitoringService)
        self.assertIn('"runtime_files_modified": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
