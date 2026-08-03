from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFETY_FALSE_FIELDS = (
    "broker_write_enabled",
    "order_submission_enabled",
    "live_trading_enabled",
    "external_network_enabled",
    "continuous_loop_enabled",
    "windows_task_enabled",
    "automatic_broker_execution_enabled",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def certificate_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_paper_stability_runtime_readiness(
    *,
    multi_day_result_path: Path,
    daily_ledger_path: Path,
    policy_path: Path,
    certificate_path: Path,
    runtime_policy_path: Path,
    audit_path: Path,
    dashboard_path: Path,
    result_path: Path,
    observed_at_override: str = "",
) -> dict[str, Any]:
    observed = (
        datetime.fromisoformat(observed_at_override)
        if observed_at_override
        else datetime.now(timezone.utc)
    )
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    observed_at = observed.isoformat()

    issues: list[dict[str, Any]] = []
    try:
        source = load_json(multi_day_result_path)
    except Exception as exc:
        source = {}
        issues.append({"code": "INVALID_MULTI_DAY_RESULT", "blocking": True, "detail": str(exc)})

    try:
        ledger = load_jsonl(daily_ledger_path)
    except Exception as exc:
        ledger = []
        issues.append({"code": "INVALID_MULTI_DAY_LEDGER", "blocking": True, "detail": str(exc)})

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({"code": "INVALID_STABILITY_POLICY", "blocking": True, "detail": str(exc)})

    if not source:
        issues.append({"code": "MULTI_DAY_RESULT_NOT_FOUND", "blocking": True, "detail": str(multi_day_result_path)})
    if not policy:
        issues.append({"code": "STABILITY_POLICY_NOT_FOUND", "blocking": True, "detail": str(policy_path)})

    unique_dates = sorted({
        str(row.get("validation_date"))
        for row in ledger
        if row.get("validation_date")
    })
    duplicate_count = max(0, len(ledger) - len(unique_dates))
    minimum_days = int(policy.get("minimum_validation_days", 3))
    source_completed_days = int(source.get("completed_days", 0))
    completed_days = max(source_completed_days, len(unique_dates))
    requirement_met = completed_days >= minimum_days

    unsafe_rows = []
    for index, row in enumerate(ledger):
        safe = row.get("paper_only") is True
        safe = safe and all(row.get(field) is False for field in SAFETY_FALSE_FIELDS if field in row)
        safe = safe and int(row.get("actual_paper_orders_submitted", 0)) == 0
        safe = safe and int(row.get("live_orders_submitted", 0)) == 0
        safe = safe and int(row.get("network_requests_executed", 0)) == 0
        safe = safe and int(row.get("write_requests_executed", 0)) == 0
        if not safe:
            unsafe_rows.append(index + 1)

    policy_safe = policy.get("paper_only") is True and all(
        policy.get(field) is False for field in SAFETY_FALSE_FIELDS
    )
    if not policy_safe:
        issues.append({"code": "STABILITY_POLICY_UNSAFE", "blocking": True, "detail": ""})
    if unsafe_rows:
        issues.append({"code": "UNSAFE_LEDGER_ROWS", "blocking": True, "detail": unsafe_rows})
    if duplicate_count:
        issues.append({"code": "DUPLICATE_LEDGER_ROWS", "blocking": True, "detail": duplicate_count})

    ledger_hash = sha256_file(daily_ledger_path)
    source_hash = sha256_file(multi_day_result_path)

    checks = {
        "source_available": bool(source),
        "source_status_pass": source.get("status") == "PASS",
        "ledger_parseable": not any(i["code"] == "INVALID_MULTI_DAY_LEDGER" for i in issues),
        "unique_dates_only": duplicate_count == 0,
        "safety_consistent": not unsafe_rows,
        "policy_safe": policy_safe,
        "paper_orders_zero": all(int(row.get("actual_paper_orders_submitted", 0)) == 0 for row in ledger),
        "live_orders_zero": all(int(row.get("live_orders_submitted", 0)) == 0 for row in ledger),
        "network_requests_zero": all(int(row.get("network_requests_executed", 0)) == 0 for row in ledger),
        "write_requests_zero": all(int(row.get("write_requests_executed", 0)) == 0 for row in ledger),
    }
    passed_count = sum(1 for value in checks.values() if value)
    stability_score = round((passed_count / len(checks)) * 100, 2)

    blocking = any(item.get("blocking") for item in issues)
    certification_eligible = (
        not blocking
        and requirement_met
        and source.get("status") == "PASS"
        and stability_score >= float(policy.get("minimum_stability_score", 100))
    )

    certificate_written = False
    certificate_valid = False
    certificate = {}
    if certification_eligible:
        body = {
            "stage": "V83.84",
            "state": "PAPER_STABILITY_CERTIFIED",
            "source_stage_range": source.get("stage_range", ""),
            "validation_dates": unique_dates,
            "completed_days": completed_days,
            "minimum_days": minimum_days,
            "stability_score": stability_score,
            "ledger_sha256": ledger_hash,
            "source_result_sha256": source_hash,
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "certified_at": observed_at,
        }
        certificate = {**body, "certificate_sha256": certificate_digest(body)}
        write_json(certificate_path, certificate)
        certificate_written = True
        certificate_valid = certificate["certificate_sha256"] == certificate_digest(body)
    elif certificate_path.exists():
        try:
            certificate = load_json(certificate_path)
            digest = certificate.pop("certificate_sha256", "")
            certificate_valid = digest == certificate_digest(certificate)
            certificate["certificate_sha256"] = digest
        except Exception:
            certificate_valid = False

    runtime_policy = {
        "stage": "V83.86",
        "state": "EXTENDED_PAPER_RUNTIME_READY" if certification_eligible else "EXTENDED_PAPER_RUNTIME_PENDING",
        "paper_only": True,
        "manual_execution_only": True,
        "supervised_execution_required": True,
        "restart_recovery_required": True,
        "stale_lock_detection_required": True,
        "duplicate_cycle_protection_required": True,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "automatic_broker_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "certificate_required": True,
        "certificate_valid": certificate_valid,
        "observed_at": observed_at,
    }
    write_json(runtime_policy_path, runtime_policy)

    recovery_checks = {
        "certificate_gate_present": runtime_policy["certificate_required"],
        "manual_execution_only": runtime_policy["manual_execution_only"],
        "supervision_required": runtime_policy["supervised_execution_required"],
        "restart_recovery_required": runtime_policy["restart_recovery_required"],
        "stale_lock_detection_required": runtime_policy["stale_lock_detection_required"],
        "duplicate_cycle_protection_required": runtime_policy["duplicate_cycle_protection_required"],
        "continuous_loop_disabled": runtime_policy["continuous_loop_enabled"] is False,
        "windows_task_disabled": runtime_policy["windows_task_enabled"] is False,
    }
    recovery_ready = all(recovery_checks.values())

    if blocking:
        state = "PAPER_STABILITY_CERTIFICATION_BLOCKED"
        status = "BLOCKED"
    elif certification_eligible and certificate_valid and recovery_ready:
        state = "EXTENDED_PAPER_RUNTIME_READY"
        status = "PASS"
    else:
        state = "PAPER_STABILITY_CERTIFICATION_PENDING"
        status = "PASS"

    audit = {
        "stage": "V83.81-V83.87",
        "state": state,
        "status": status,
        "checks": checks,
        "recovery_checks": recovery_checks,
        "stability_score": stability_score,
        "completed_days": completed_days,
        "minimum_days": minimum_days,
        "remaining_days": max(0, minimum_days - completed_days),
        "requirement_met": requirement_met,
        "certification_eligible": certification_eligible,
        "certificate_written": certificate_written,
        "certificate_valid": certificate_valid,
        "ledger_sha256": ledger_hash,
        "source_result_sha256": source_hash,
        "validation_dates": unique_dates,
        "issues": issues,
        "observed_at": observed_at,
    }
    write_json(audit_path, audit)

    dashboard = {
        **audit,
        "stage": "V83.88",
        "paper_stability_runtime_state": state,
        "extended_runtime_ready": state == "EXTENDED_PAPER_RUNTIME_READY",
        "paper_only": True,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "automatic_broker_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
    }
    write_json(dashboard_path, dashboard)

    result = {
        **dashboard,
        "stage_range": "V83.81-V83.88",
        "implementation_type": "PAPER_STABILITY_AND_RUNTIME_READINESS",
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "blocking_issue_count": sum(1 for item in issues if item.get("blocking")),
        "issue_count": len(issues),
        "next_phase": (
            "V83_89_PAPER_PERFORMANCE_EVALUATION"
            if state == "EXTENDED_PAPER_RUNTIME_READY"
            else "V83_81_TO_V83_88_AWAIT_MULTI_DAY_COMPLETION"
            if status == "PASS"
            else "V83_81_TO_V83_88_RECOVER"
        ),
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
