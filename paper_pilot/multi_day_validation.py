from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            records.append(value)
    return records


class MultiDayPaperValidationFoundation:
    def run(
        self,
        *,
        policy_path: Path,
        foundation_result_path: Path,
        session_result_path: Path,
        performance_result_path: Path,
        risk_result_path: Path,
        automation_result_path: Path,
        validation_ledger_path: Path,
        daily_record_path: Path,
        validation_summary_path: Path,
        validation_gate_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        record_validation_day: bool = False,
        validation_date: str | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        loaded: dict[str, dict[str, Any]] = {}

        for name, path in (
            ("VALIDATION_POLICY", policy_path),
            ("FOUNDATION_RESULT", foundation_result_path),
            ("SESSION_RESULT", session_result_path),
            ("PERFORMANCE_RESULT", performance_result_path),
            ("RISK_RESULT", risk_result_path),
            ("AUTOMATION_RESULT", automation_result_path),
        ):
            try:
                payload = _load(path)
            except Exception as exc:
                payload = {}
                issues.append({
                    "code": f"INVALID_{name}",
                    "blocking": True,
                    "detail": str(exc),
                })
            if not payload:
                issues.append({
                    "code": f"{name}_NOT_FOUND",
                    "blocking": True,
                    "detail": str(path),
                })
            loaded[name] = payload

        policy = loaded["VALIDATION_POLICY"]
        foundation = loaded["FOUNDATION_RESULT"]
        session = loaded["SESSION_RESULT"]
        performance = loaded["PERFORMANCE_RESULT"]
        risk = loaded["RISK_RESULT"]
        automation = loaded["AUTOMATION_RESULT"]

        policy_ready = False
        if policy:
            checks = [
                ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
                ("READ_ONLY_REQUIRED", bool(policy.get("read_only", False))),
                (
                    "BROKER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("broker_write_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "MINIMUM_DAYS_INVALID",
                    2 <= int(policy.get("minimum_validation_days", 0)) <= 60,
                ),
                (
                    "CONSECUTIVE_DAYS_INVALID",
                    1 <= int(policy.get("minimum_consecutive_healthy_days", 0))
                    <= int(policy.get("minimum_validation_days", 0)),
                ),
                (
                    "MAXIMUM_RECORDS_INVALID",
                    10 <= int(policy.get("maximum_validation_records", 0)) <= 365,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "validation policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        pilot_started = bool(foundation.get("pilot_started", False))
        pilot_id = str(foundation.get("pilot_id", "")).strip()
        session_id = str(foundation.get("session_id", "")).strip()
        session_health = str(session.get("health_status", "WAITING")).upper()
        risk_state = str(risk.get("state", ""))
        emergency_stop_required = bool(
            risk.get("emergency_stop_required", False)
        )
        automation_state = str(automation.get("state", ""))
        recovery_gate_clear = bool(
            automation.get("recovery_gate_clear", False)
        )
        snapshot_ready = bool(automation.get("snapshot_ready", False))

        day_healthy = bool(
            pilot_started
            and session_health == "HEALTHY"
            and risk_state == "PAPER_RISK_HEALTHY"
            and not emergency_stop_required
            and recovery_gate_clear
            and snapshot_ready
        )

        chosen_date = validation_date or date.today().isoformat()
        try:
            date.fromisoformat(chosen_date)
        except ValueError:
            issues.append({
                "code": "VALIDATION_DATE_INVALID",
                "blocking": True,
                "detail": chosen_date,
            })

        records = _read_jsonl(validation_ledger_path)
        duplicate_date = any(
            str(item.get("validation_date", "")) == chosen_date
            for item in records
        )
        if record_validation_day and duplicate_date:
            issues.append({
                "code": "DUPLICATE_VALIDATION_DATE",
                "blocking": True,
                "detail": chosen_date,
            })

        observed_at = datetime.now(timezone.utc).isoformat()
        record_written = False

        if (
            record_validation_day
            and pilot_started
            and policy_ready
            and not duplicate_date
            and not any(item.get("blocking") for item in issues)
        ):
            record = {
                "stage": "OP5.01",
                "validation_date": chosen_date,
                "pilot_id": pilot_id,
                "session_id": session_id,
                "session_health": session_health,
                "performance_state": performance.get("state", ""),
                "risk_state": risk_state,
                "automation_state": automation_state,
                "snapshot_ready": snapshot_ready,
                "recovery_gate_clear": recovery_gate_clear,
                "emergency_stop_required": emergency_stop_required,
                "latest_equity": float(
                    performance.get("latest_equity", 0) or 0
                ),
                "cumulative_return_pct": float(
                    performance.get("cumulative_return_pct", 0) or 0
                ),
                "max_drawdown_pct": float(
                    risk.get("max_drawdown_pct", 0) or 0
                ),
                "daily_loss_pct": float(
                    risk.get("daily_loss_pct", 0) or 0
                ),
                "gross_exposure_pct": float(
                    risk.get("gross_exposure_pct", 0) or 0
                ),
                "day_healthy": day_healthy,
                "paper_only": True,
                "recorded_at": observed_at,
            }
            _append(validation_ledger_path, record)
            records.append(record)
            record_written = True
            _write(daily_record_path, record)

            maximum_records = int(policy["maximum_validation_records"])
            if len(records) > maximum_records:
                records = records[-maximum_records:]
                validation_ledger_path.write_text(
                    "".join(
                        json.dumps(item, sort_keys=True) + "\n"
                        for item in records
                    ),
                    encoding="utf-8",
                )

        validation_days = len(records)
        healthy_days = sum(
            1 for item in records if item.get("day_healthy") is True
        )
        unhealthy_days = validation_days - healthy_days

        consecutive_healthy_days = 0
        for item in reversed(records):
            if item.get("day_healthy") is True:
                consecutive_healthy_days += 1
            else:
                break

        required_days = int(
            policy.get("minimum_validation_days", 0) or 0
        )
        required_consecutive = int(
            policy.get("minimum_consecutive_healthy_days", 0) or 0
        )
        validation_complete = bool(
            validation_days >= required_days
            and consecutive_healthy_days >= required_consecutive
            and unhealthy_days <= int(
                policy.get("maximum_unhealthy_days", 0) or 0
            )
        )

        summary = {
            "stage": "OP5.02",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "validation_days": validation_days,
            "healthy_days": healthy_days,
            "unhealthy_days": unhealthy_days,
            "consecutive_healthy_days": consecutive_healthy_days,
            "minimum_validation_days": required_days,
            "minimum_consecutive_healthy_days": required_consecutive,
            "maximum_unhealthy_days": int(
                policy.get("maximum_unhealthy_days", 0) or 0
            ),
            "validation_complete": validation_complete,
            "paper_only": True,
            "observed_at": observed_at,
        }
        _write(validation_summary_path, summary)

        gate_reasons: list[str] = []
        if not pilot_started:
            gate_reasons.append("PILOT_NOT_STARTED")
        if validation_days < required_days:
            gate_reasons.append("MINIMUM_VALIDATION_DAYS_NOT_MET")
        if consecutive_healthy_days < required_consecutive:
            gate_reasons.append("CONSECUTIVE_HEALTHY_DAYS_NOT_MET")
        if unhealthy_days > int(
            policy.get("maximum_unhealthy_days", 0) or 0
        ):
            gate_reasons.append("MAXIMUM_UNHEALTHY_DAYS_EXCEEDED")
        if emergency_stop_required:
            gate_reasons.append("EMERGENCY_STOP_REQUIRED")
        if not recovery_gate_clear:
            gate_reasons.append("RECOVERY_GATE_NOT_CLEAR")

        _write(validation_gate_path, {
            "stage": "OP5.03",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "validation_complete": validation_complete,
            "validation_gate_clear": not gate_reasons,
            "gate_reasons": gate_reasons,
            "broker_action_performed": False,
            "paper_only": True,
            "created_at": observed_at,
        })

        if any(item.get("blocking") for item in issues):
            state, status = "MULTI_DAY_VALIDATION_SAFE_MODE", "BLOCKED"
        elif not pilot_started:
            state, status = "WAIT_PILOT_START", "PASS"
        elif validation_complete:
            state, status = "MULTI_DAY_VALIDATION_COMPLETE", "PASS"
        elif record_written:
            state, status = "MULTI_DAY_VALIDATION_DAY_RECORDED", "PASS"
        else:
            state, status = "MULTI_DAY_VALIDATION_IN_PROGRESS", "PASS"

        _write(dashboard_state_path, {
            "stage": "OP5.04",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "validation_state": state,
            "validation_days": validation_days,
            "healthy_days": healthy_days,
            "unhealthy_days": unhealthy_days,
            "consecutive_healthy_days": consecutive_healthy_days,
            "validation_complete": validation_complete,
            "day_healthy": day_healthy,
            "gate_reasons": gate_reasons,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": observed_at,
        })

        blocking = sum(
            1 for item in issues if item.get("blocking")
        )
        result = {
            "stage_range": "OP5.01-OP5.04",
            "implementation_type": (
                "MULTI_DAY_PAPER_VALIDATION_FOUNDATION"
            ),
            "status": status,
            "state": state,
            "pilot_id": pilot_id,
            "session_id": session_id,
            "pilot_started": pilot_started,
            "record_validation_day_requested": (
                record_validation_day
            ),
            "validation_date": chosen_date,
            "duplicate_validation_date": duplicate_date,
            "record_written": record_written,
            "day_healthy": day_healthy,
            "validation_days": validation_days,
            "healthy_days": healthy_days,
            "unhealthy_days": unhealthy_days,
            "consecutive_healthy_days": consecutive_healthy_days,
            "validation_complete": validation_complete,
            "validation_summary_written": True,
            "validation_gate_written": True,
            "dashboard_state_written": True,
            "gate_reasons": gate_reasons,
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "cancel_enabled": False,
            "position_close_enabled": False,
            "continuous_loop_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": blocking > 0,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP5_05_TO_OP5_08_VALIDATION_ANALYTICS"
                if validation_complete
                else "OP5_01_TO_OP5_04_CONTINUE_VALIDATION"
            ),
            "validation_mode": (
                "LOCAL_MULTI_DAY_PAPER_VALIDATION_ONLY"
            ),
            "observed_at": observed_at,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
