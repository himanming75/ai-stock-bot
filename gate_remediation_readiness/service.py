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
from .process_normalizer import normalize_controller_processes


class GateRemediationReadinessService:
    def evaluate(
        self,
        *,
        repository_root: Path,
        output_dir: Path,
        policy_path: Path,
        processes: list[dict] | None = None,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        policy = read_json_optional(policy_path)
        gate = read_json_optional(
            repository_root
            / "release/v371_380_autonomous_paper_operations_gate/"
            "actual/autonomous_gate_latest.json"
        )
        health = read_json_optional(
            repository_root
            / "release/v351_360_system_health_monitoring/"
            "actual/system_health_latest.json"
        )
        controller = read_json_optional(
            repository_root
            / "release/paper_automation_controller/actual/"
            "controller_summary.json"
        )
        checkpoint = read_json_optional(
            repository_root
            / "release/paper_automation_controller/actual/checkpoint.json"
        )

        watchdog_root = (
            repository_root
            / "release/automation_watchdog_restart_recovery/actual"
        )
        watchdog_summary_path = watchdog_root / "watchdog_summary.json"
        watchdog_summary = read_json_optional(watchdog_summary_path)
        watchdog_source = "watchdog_summary.json"

        if not watchdog_summary:
            watchdog_summary = read_json_optional(
                watchdog_root / "watchdog_state.json"
            )
            watchdog_source = "watchdog_state.json"

        if not watchdog_summary:
            ledger = read_jsonl(
                watchdog_root / "watchdog_ledger.jsonl"
            )
            watchdog_summary = ledger[-1] if ledger else {}
            watchdog_source = (
                "watchdog_ledger.jsonl:last_record"
                if ledger else "NONE"
            )

        derived_watchdog_summary = {
            "derived": True,
            "source": watchdog_source,
            "original_summary_exists": watchdog_summary_path.exists(),
            "status": watchdog_summary.get("status"),
            "action": watchdog_summary.get("action"),
            "stop_reason": watchdog_summary.get("stop_reason"),
            "restart_count": watchdog_summary.get("restart_count"),
            "generated_at": now.isoformat(),
            "runtime_files_modified": False,
        }

        process_health = normalize_controller_processes(
            processes
            if processes is not None
            else health.get("process_health", {}).get("processes", [])
        )

        original_blockers = list(gate.get("blockers", []))
        normalized_blockers = []
        resolved_by_normalization = []

        for blocker in original_blockers:
            if blocker == "HEALTH_CRITICAL:DUPLICATE_CONTROLLER_ROOTS":
                if not process_health["duplicate_controller_confirmed"]:
                    resolved_by_normalization.append(blocker)
                    continue
            if blocker in {
                "HEALTH_WARNING:CONTROLLER_HEARTBEAT_STALE_OR_MISSING",
                "HEALTH_WARNING:CONTROLLER_LOCK_STALE",
            }:
                if controller.get("status") == "PASS" and checkpoint:
                    resolved_by_normalization.append(blocker)
                    continue
            normalized_blockers.append(blocker)

        remediation = []
        mapping = {
            "AUTONOMOUS_SUBMISSION_HARD_DISABLED": (
                "KEEP_BLOCKED",
                "This is the intended safety control. Do not enable it "
                "until certification and a separate approval-token stage."
            ),
            "HEALTH_WARNING:DISK_USAGE_HIGH": (
                "MANUAL_ACTION",
                "Free disk space or archive old release bundles outside "
                "the repository, then rerun Health and Gate.",
            ),
            "HEALTH_WARNING:REPOSITORY_FILE_OVER_100MB": (
                "MANUAL_ACTION",
                "Move large generated bundles out of the Git working tree "
                "or add an approved retention/ignore policy.",
            ),
            "CRITICAL_NOTIFICATION_COUNT:1": (
                "RERUN_AFTER_HEALTH_REFRESH",
                "Regenerate Health, Notification, and Gate snapshots after "
                "the underlying health blockers are resolved.",
            ),
        }

        for blocker in normalized_blockers:
            action_type, instruction = mapping.get(
                blocker,
                (
                    "REVIEW_REQUIRED",
                    "Review the current source snapshot and rerun the "
                    "upstream monitor before certification.",
                ),
            )
            remediation.append(
                {
                    "blocker": blocker,
                    "action_type": action_type,
                    "instruction": instruction,
                    "automatic_action_performed": False,
                }
            )

        operational_blockers = [
            item for item in normalized_blockers
            if item != "AUTONOMOUS_SUBMISSION_HARD_DISABLED"
        ]
        readiness_level = (
            "NOT_READY"
            if operational_blockers
            else "OPERATIONALLY_READY_SUBMISSION_DISABLED"
        )
        certificate_status = (
            "BLOCKED_CERTIFICATE"
            if operational_blockers
            else "CONDITIONAL_READINESS_CERTIFICATE"
        )

        certificate_payload = {
            "generated_at": now.isoformat(),
            "readiness_level": readiness_level,
            "certificate_status": certificate_status,
            "normalized_blockers": normalized_blockers,
            "resolved_by_normalization": resolved_by_normalization,
            "controller_status": controller.get("status"),
            "controller_cycle": checkpoint.get("cycle_number"),
            "watchdog_source": watchdog_source,
            "process_health": process_health,
        }
        certificate_id = "readiness_" + hashlib.sha256(
            json.dumps(
                certificate_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:24]

        result = {
            "stage": (
                "V381_TO_V390_GATE_REMEDIATION_AND_READINESS_CERTIFICATE"
            ),
            "status": certificate_status,
            "generated_at": now.isoformat(),
            "certificate_id": certificate_id,
            "readiness_level": readiness_level,
            "original_gate_status": gate.get("status"),
            "original_blockers": original_blockers,
            "normalized_blockers": normalized_blockers,
            "resolved_by_normalization": resolved_by_normalization,
            "process_normalization": process_health,
            "derived_watchdog_summary": derived_watchdog_summary,
            "remediation_plan": remediation,
            "operational_blocker_count": len(operational_blockers),
            "submission_safety_block_present": (
                "AUTONOMOUS_SUBMISSION_HARD_DISABLED"
                in normalized_blockers
            ),
            "autonomous_paper_operations_allowed": False,
            "paper_order_submission_enabled": False,
            "actual_remediation_action_performed": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V391_TO_V400_AUTONOMOUS_PAPER_CERTIFICATION"
            ),
        }

        write_json(
            output_dir / "derived_watchdog_summary.json",
            derived_watchdog_summary,
        )
        write_json(
            output_dir / "readiness_certificate.json",
            result,
        )
        write_json(
            output_dir / "remediation_plan.json",
            {
                "certificate_id": certificate_id,
                "generated_at": now.isoformat(),
                "items": remediation,
                "automatic_actions_performed": 0,
            },
        )
        write_json(
            output_dir / "readiness_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "certificate_id": certificate_id,
                "readiness_level": readiness_level,
                "original_blocker_count": len(original_blockers),
                "normalized_blocker_count": len(normalized_blockers),
                "resolved_by_normalization_count": len(
                    resolved_by_normalization
                ),
                "operational_blocker_count": len(operational_blockers),
                "autonomous_submission": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        append_jsonl(
            output_dir / "readiness_certificate_ledger.jsonl",
            result,
        )
        return result
