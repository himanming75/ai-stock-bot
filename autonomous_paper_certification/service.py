from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .io import (
    append_jsonl,
    read_json_optional,
    read_jsonl,
    write_json,
)


class AutonomousPaperCertificationService:
    def evaluate(
        self,
        *,
        repository_root: Path,
        policy_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        policy = read_json_optional(policy_path)

        controller_root = (
            repository_root
            / "release/paper_automation_controller/actual"
        )
        controller_summary = read_json_optional(
            controller_root / "controller_summary.json"
        )
        controller_cycles = read_jsonl(
            controller_root / "controller_cycle_ledger.jsonl"
        )
        checkpoint = read_json_optional(
            controller_root / "checkpoint.json"
        )

        watchdog = read_json_optional(
            repository_root
            / "release/automation_watchdog_restart_recovery/"
            "actual/watchdog_summary.json"
        )
        session = read_json_optional(
            repository_root
            / "release/daily_session_manager_startup_autorun/"
            "actual/daily_session_summary.json"
        )
        risk = read_json_optional(
            repository_root
            / "release/v331_340_realtime_risk_monitoring/"
            "actual/risk_monitor_latest.json"
        )
        health = read_json_optional(
            repository_root
            / "release/v351_360_system_health_monitoring/"
            "actual/system_health_latest.json"
        )
        readiness = read_json_optional(
            repository_root
            / "release/v381_390_gate_remediation_readiness/"
            "actual/readiness_certificate.json"
        )
        gate = read_json_optional(
            repository_root
            / "release/v371_380_autonomous_paper_operations_gate/"
            "actual/autonomous_gate_latest.json"
        )

        minimum_cycles = int(
            policy.get("minimum_controller_cycles", 60)
        )
        completed_cycles = len(controller_cycles)
        error_cycles = [
            item for item in controller_cycles
            if item.get("errors")
        ]
        broker_write_cycles = [
            item for item in controller_cycles
            if item.get("actual_broker_write_performed")
        ]
        paper_order_count = sum(
            int(item.get("actual_paper_orders_submitted", 0) or 0)
            for item in controller_cycles
        )
        live_order_count = sum(
            int(item.get("actual_live_orders_submitted", 0) or 0)
            for item in controller_cycles
        )
        cycle_numbers = [
            int(item.get("cycle_number", 0) or 0)
            for item in controller_cycles
            if item.get("cycle_number") is not None
        ]
        unique_cycle_count = len(set(cycle_numbers))
        duplicate_cycle_count = max(
            0, len(cycle_numbers) - unique_cycle_count
        )

        market_open_observed = any(
            item.get("market_is_open") is True
            for item in controller_cycles
        )
        market_closed_observed = any(
            item.get("market_is_open") is False
            for item in controller_cycles
        )
        market_close_stop_observed = (
            controller_summary.get("stopped_reason")
            in {"MARKET_CLOSED", "MARKET_CLOSED_IDLE"}
            or controller_summary.get("stop_reason")
            in {"MARKET_CLOSED", "MARKET_CLOSED_IDLE"}
        )
        next_day_autostart_observed = bool(
            session.get("next_trading_day_autostart_validated", False)
        )

        checks = []

        def add(name, passed, required=True, details=None):
            checks.append(
                {
                    "name": name,
                    "passed": bool(passed),
                    "required": bool(required),
                    "details": details or {},
                }
            )

        add(
            "MINIMUM_CONTROLLER_CYCLES",
            completed_cycles >= minimum_cycles,
            True,
            {
                "completed_cycles": completed_cycles,
                "minimum_cycles": minimum_cycles,
            },
        )
        add(
            "CONTROLLER_ERRORS_ZERO",
            len(error_cycles) == 0,
            True,
            {"error_cycle_count": len(error_cycles)},
        )
        add(
            "BROKER_WRITES_ZERO",
            len(broker_write_cycles) == 0,
            True,
            {"broker_write_cycle_count": len(broker_write_cycles)},
        )
        add(
            "PAPER_ORDERS_ZERO_DURING_READ_ONLY_CERTIFICATION",
            paper_order_count == 0,
            True,
            {"paper_order_count": paper_order_count},
        )
        add(
            "LIVE_ORDERS_ZERO",
            live_order_count == 0,
            True,
            {"live_order_count": live_order_count},
        )
        add(
            "NO_DUPLICATE_CYCLE_NUMBERS",
            duplicate_cycle_count == 0,
            True,
            {"duplicate_cycle_count": duplicate_cycle_count},
        )
        add(
            "WATCHDOG_PASS",
            watchdog.get("status") == "PASS",
            True,
            {
                "status": watchdog.get("status"),
                "stop_reason": watchdog.get("stop_reason"),
            },
        )
        add(
            "READINESS_CERTIFICATE_PRESENT",
            readiness.get("status")
            in {
                "CONDITIONAL_READINESS_CERTIFICATE",
                "FULL_READINESS_CERTIFICATE",
            },
            True,
            {
                "status": readiness.get("status"),
                "readiness_level": readiness.get("readiness_level"),
            },
        )
        add(
            "RISK_NOT_CRITICAL",
            risk.get("risk_level") in {"NORMAL", "WARNING"},
            True,
            {"risk_level": risk.get("risk_level")},
        )
        add(
            "HEALTH_EVIDENCE_PRESENT",
            bool(health),
            True,
            {"health_status": health.get("status")},
        )
        add(
            "MARKET_OPEN_OBSERVED",
            market_open_observed,
            True,
            {"observed": market_open_observed},
        )
        add(
            "MARKET_CLOSED_OBSERVED",
            market_closed_observed,
            False,
            {"observed": market_closed_observed},
        )
        add(
            "MARKET_CLOSE_AUTO_STOP_OBSERVED",
            market_close_stop_observed,
            False,
            {
                "observed": market_close_stop_observed,
                "controller_stopped_reason": (
                    controller_summary.get("stopped_reason")
                    or controller_summary.get("stop_reason")
                ),
            },
        )
        add(
            "NEXT_TRADING_DAY_AUTOSTART_OBSERVED",
            next_day_autostart_observed,
            False,
            {"observed": next_day_autostart_observed},
        )
        add(
            "AUTONOMOUS_SUBMISSION_HARD_DISABLED",
            not bool(
                gate.get(
                    "autonomous_paper_operations_allowed",
                    False,
                )
            ),
            True,
            {
                "autonomous_paper_operations_allowed": gate.get(
                    "autonomous_paper_operations_allowed"
                )
            },
        )

        failed_required = [
            item for item in checks
            if item["required"] and not item["passed"]
        ]
        pending_market_evidence = [
            item for item in checks
            if not item["required"] and not item["passed"]
        ]

        if failed_required:
            certification_status = "NOT_CERTIFIED"
            certification_level = "READ_ONLY_CERTIFICATION_BLOCKED"
        elif pending_market_evidence:
            certification_status = "CONDITIONAL_CERTIFICATION"
            certification_level = (
                "READ_ONLY_AUTONOMOUS_PAPER_CORE_CERTIFIED_"
                "PENDING_MARKET_LIFECYCLE_EVIDENCE"
            )
        else:
            certification_status = "FULL_CERTIFICATION"
            certification_level = (
                "READ_ONLY_AUTONOMOUS_PAPER_OPERATIONS_CERTIFIED"
            )

        evidence = {
            "completed_cycles": completed_cycles,
            "last_checkpoint_cycle": checkpoint.get("cycle_number"),
            "controller_status": controller_summary.get("status"),
            "watchdog_status": watchdog.get("status"),
            "watchdog_stop_reason": watchdog.get("stop_reason"),
            "session_status": session.get("status"),
            "risk_level": risk.get("risk_level"),
            "health_status": health.get("status"),
            "readiness_status": readiness.get("status"),
            "gate_status": gate.get("status"),
            "paper_orders_during_certification": paper_order_count,
            "live_orders_during_certification": live_order_count,
        }
        certificate_seed = {
            "generated_at": now.isoformat(),
            "certification_status": certification_status,
            "certification_level": certification_level,
            "checks": checks,
            "evidence": evidence,
        }
        certificate_id = "paper_cert_" + hashlib.sha256(
            json.dumps(
                certificate_seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:24]

        result = {
            "stage": "V391_TO_V400_AUTONOMOUS_PAPER_CERTIFICATION",
            "status": certification_status,
            "certification_level": certification_level,
            "certificate_id": certificate_id,
            "generated_at": now.isoformat(),
            "checks": checks,
            "required_check_count": sum(
                1 for item in checks if item["required"]
            ),
            "required_check_pass_count": sum(
                1
                for item in checks
                if item["required"] and item["passed"]
            ),
            "failed_required_checks": [
                item["name"] for item in failed_required
            ],
            "pending_market_evidence": [
                item["name"] for item in pending_market_evidence
            ],
            "evidence": evidence,
            "autonomous_paper_operations_allowed": False,
            "paper_order_submission_enabled": False,
            "live_order_submission_enabled": False,
            "separate_approval_token_required": True,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V401_TO_V410_APPROVAL_TOKEN_PAPER_AUTOMATION_ENABLEMENT"
            ),
            "next_market_validation": (
                "MARKET_CLOSE_AUTO_STOP_AND_NEXT_DAY_AUTOSTART"
            ),
        }

        write_json(
            output_dir / "autonomous_paper_certificate.json",
            result,
        )
        write_json(
            output_dir / "certification_checklist.json",
            {
                "certificate_id": certificate_id,
                "checks": checks,
                "failed_required_checks": result[
                    "failed_required_checks"
                ],
                "pending_market_evidence": result[
                    "pending_market_evidence"
                ],
            },
        )
        write_json(
            output_dir / "certification_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "certificate_id": certificate_id,
                "status": certification_status,
                "certification_level": certification_level,
                "completed_cycles": completed_cycles,
                "required_check_pass_count": result[
                    "required_check_pass_count"
                ],
                "required_check_count": result[
                    "required_check_count"
                ],
                "failed_required_check_count": len(
                    failed_required
                ),
                "pending_market_evidence_count": len(
                    pending_market_evidence
                ),
                "paper_submission_enabled": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        append_jsonl(
            output_dir / "autonomous_paper_certificate_ledger.jsonl",
            result,
        )
        return result
