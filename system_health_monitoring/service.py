from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .io_checks import (
    read_json_optional,
    validate_json,
    validate_jsonl,
)
from .process_checks import (
    classify_controller_processes,
    windows_process_snapshot,
)
from .resource_checks import disk_health, repository_size


class SystemHealthMonitoringService:
    def __init__(
        self,
        *,
        process_provider: Callable[[], list[dict]] | None = None,
        now_provider=None,
    ) -> None:
        self.process_provider = process_provider or windows_process_snapshot
        self.now_provider = now_provider or (
            lambda: datetime.now(timezone.utc)
        )

    @staticmethod
    def _parse_time(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError:
            return None

    def evaluate(
        self,
        *,
        repository_root: Path,
        output_dir: Path,
        policy_path: Path,
    ) -> dict:
        policy = json.loads(
            policy_path.read_text(encoding="utf-8-sig")
        )
        now = self.now_provider()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        controller_actual = (
            repository_root
            / "release/paper_automation_controller/actual"
        )
        watchdog_actual = (
            repository_root
            / "release/automation_watchdog_restart_recovery/actual"
        )
        session_actual = (
            repository_root
            / "release/daily_session_manager_startup_autorun/actual"
        )

        json_paths = [
            controller_actual / "checkpoint.json",
            controller_actual / "controller_summary.json",
            watchdog_actual / "watchdog_state.json",
            watchdog_actual / "watchdog_summary.json",
            session_actual / "daily_session_state.json",
            session_actual / "daily_session_summary.json",
            repository_root
            / "release/v321_330_realtime_portfolio_monitoring/actual/"
            "portfolio_monitor_latest.json",
            repository_root
            / "release/v331_340_realtime_risk_monitoring/actual/"
            "risk_monitor_latest.json",
            repository_root
            / "release/v341_350_performance_analytics/actual/"
            "performance_analytics_latest.json",
        ]
        jsonl_paths = [
            controller_actual / "controller_cycle_ledger.jsonl",
            watchdog_actual / "watchdog_ledger.jsonl",
            session_actual / "daily_session_ledger.jsonl",
            repository_root
            / "release/actual_market_polling_validation/actual/"
            "polling_ledger.jsonl",
        ]

        json_checks = [validate_json(path) for path in json_paths]
        jsonl_checks = [
            validate_jsonl(
                path,
                tail_limit=int(policy["jsonl_tail_validation_limit"]),
            )
            for path in jsonl_paths
        ]

        checkpoint = read_json_optional(
            controller_actual / "checkpoint.json"
        )
        controller_summary = read_json_optional(
            controller_actual / "controller_summary.json"
        )
        watchdog_summary = read_json_optional(
            watchdog_actual / "watchdog_summary.json"
        )
        daily_summary = read_json_optional(
            session_actual / "daily_session_summary.json"
        )

        heartbeat_value = (
            checkpoint.get("completed_at")
            or checkpoint.get("updated_at")
            or checkpoint.get("generated_at")
        )
        heartbeat_time = self._parse_time(heartbeat_value)
        heartbeat_age_seconds = (
            max(0.0, (now - heartbeat_time).total_seconds())
            if heartbeat_time
            else None
        )
        heartbeat_stale = (
            heartbeat_age_seconds is None
            or heartbeat_age_seconds
            > float(policy["heartbeat_warning_seconds"])
        )

        lock_path = controller_actual / "controller.lock"
        lock_exists = lock_path.exists()
        lock_age_seconds = (
            max(0.0, now.timestamp() - lock_path.stat().st_mtime)
            if lock_exists
            else None
        )
        lock_stale = (
            lock_exists
            and lock_age_seconds
            > float(policy["stale_lock_warning_seconds"])
        )

        processes = classify_controller_processes(
            self.process_provider()
        )
        disk = disk_health(repository_root)
        repo = repository_size(repository_root)

        warnings = []
        critical = []

        missing_json = [
            item["path"] for item in json_checks if not item["exists"]
        ]
        invalid_json = [
            item["path"]
            for item in json_checks
            if item["exists"] and not item["valid"]
        ]
        missing_jsonl = [
            item["path"] for item in jsonl_checks if not item["exists"]
        ]
        invalid_jsonl = [
            item["path"]
            for item in jsonl_checks
            if item["exists"] and not item["valid"]
        ]

        if missing_json:
            warnings.append("REQUIRED_JSON_MISSING")
        if missing_jsonl:
            warnings.append("REQUIRED_JSONL_MISSING")
        if invalid_json:
            critical.append("INVALID_JSON_DETECTED")
        if invalid_jsonl:
            critical.append("INVALID_JSONL_DETECTED")
        if heartbeat_stale:
            warnings.append("CONTROLLER_HEARTBEAT_STALE_OR_MISSING")
        if lock_stale:
            warnings.append("CONTROLLER_LOCK_STALE")
        if processes["duplicate_controller_detected"]:
            critical.append("DUPLICATE_CONTROLLER_ROOTS")
        if disk["used_percent"] > float(policy["disk_critical_percent"]):
            critical.append("DISK_USAGE_CRITICAL")
        elif disk["used_percent"] > float(policy["disk_warning_percent"]):
            warnings.append("DISK_USAGE_HIGH")
        if repo["files_over_100mb"]:
            warnings.append("REPOSITORY_FILE_OVER_100MB")
        if controller_summary.get("status") not in {
            None, "PASS", "PASS_WITH_WARNINGS"
        }:
            warnings.append("CONTROLLER_SUMMARY_NOT_PASS")
        if watchdog_summary.get("status") not in {
            None, "PASS", "PASS_WITH_WARNINGS"
        }:
            warnings.append("WATCHDOG_SUMMARY_NOT_PASS")
        if daily_summary.get("status") not in {
            None, "PASS", "PASS_WITH_WARNINGS"
        }:
            warnings.append("DAILY_SESSION_SUMMARY_NOT_PASS")

        status = (
            "FAIL"
            if critical
            else "PASS_WITH_WARNINGS"
            if warnings
            else "PASS"
        )

        result = {
            "stage": "V351_TO_V360_SYSTEM_HEALTH_MONITORING",
            "status": status,
            "generated_at": now.isoformat(),
            "health_score": max(
                0,
                100 - len(warnings) * 8 - len(critical) * 25,
            ),
            "warnings": warnings,
            "critical_issues": critical,
            "json_integrity": {
                "checks": json_checks,
                "missing_count": len(missing_json),
                "invalid_count": len(invalid_json),
            },
            "jsonl_integrity": {
                "checks": jsonl_checks,
                "missing_count": len(missing_jsonl),
                "invalid_count": len(invalid_jsonl),
            },
            "heartbeat": {
                "value": heartbeat_value,
                "age_seconds": heartbeat_age_seconds,
                "stale": heartbeat_stale,
                "warning_threshold_seconds": policy[
                    "heartbeat_warning_seconds"
                ],
            },
            "controller_lock": {
                "exists": lock_exists,
                "age_seconds": lock_age_seconds,
                "stale": lock_stale,
                "warning_threshold_seconds": policy[
                    "stale_lock_warning_seconds"
                ],
                "action_performed": "NONE_READ_ONLY",
            },
            "process_health": processes,
            "disk_health": disk,
            "repository_health": repo,
            "component_status": {
                "controller": controller_summary.get("status"),
                "watchdog": watchdog_summary.get("status"),
                "daily_session": daily_summary.get("status"),
                "controller_cycle": checkpoint.get("cycle_number"),
                "market_is_open": controller_summary.get("market_is_open"),
            },
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V361_TO_V370_NOTIFICATION_AND_ALERT_ROUTING"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "system_health_latest.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        dashboard = {
            "generated_at": result["generated_at"],
            "status": status,
            "health_score": result["health_score"],
            "warning_count": len(warnings),
            "critical_issue_count": len(critical),
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "heartbeat_stale": heartbeat_stale,
            "duplicate_controller_detected": processes[
                "duplicate_controller_detected"
            ],
            "controller_root_count": processes[
                "root_controller_count"
            ],
            "disk_used_percent": disk["used_percent"],
            "files_over_100mb": len(repo["files_over_100mb"]),
            "invalid_json_count": len(invalid_json),
            "invalid_jsonl_count": len(invalid_jsonl),
            "broker_write": False,
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        }
        (output_dir / "system_health_dashboard.json").write_text(
            json.dumps(dashboard, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with (output_dir / "system_health_ledger.jsonl").open(
            "a", encoding="utf-8"
        ) as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        (output_dir / "system_health_summary.json").write_text(
            json.dumps(
                {
                    "stage": result["stage"],
                    "status": status,
                    "health_score": result["health_score"],
                    "warnings": warnings,
                    "critical_issues": critical,
                    "actual_broker_write_performed": False,
                    "actual_paper_orders_submitted": 0,
                    "actual_live_orders_submitted": 0,
                    "next_fixed_development": result[
                        "next_fixed_development"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return result
