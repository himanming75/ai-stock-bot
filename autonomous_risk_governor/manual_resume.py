from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


REQUIRED_PHRASE = "APPROVE_MANUAL_RISK_RESUME"


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("RESUME_TIMESTAMP_REQUIRED")
    normalized = value.strip().replace("Z", "+00:00")
    result = datetime.fromisoformat(normalized)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def evaluate_manual_resume(
    pause_result: dict[str, Any],
    kill_switch_result: dict[str, Any],
    request: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    pause_state = str(pause_result.get("pause_state", "PAUSED"))
    pause_required = bool(pause_result.get("pause_required", True))
    kill_switch_active = bool(
        kill_switch_result.get("evaluation", {}).get("kill_switch_active", True)
    )
    kill_switch_state = str(kill_switch_result.get("state", ""))

    approval_phrase = str(request.get("approval_phrase", ""))
    requested_by = str(request.get("requested_by", "")).strip()
    reason = str(request.get("reason", "")).strip()
    expires_at = _parse_utc(request.get("expires_at"))

    checks = {
        "pause_state_resumable": pause_state in {"PAUSED", "RUNNING"},
        "pause_condition_cleared": not pause_required,
        "kill_switch_inactive": (
            not kill_switch_active
            and kill_switch_state != "KILL_SWITCH_GUARD_BLOCKED"
        ),
        "approval_phrase_valid": approval_phrase == REQUIRED_PHRASE,
        "requested_by_present": bool(requested_by),
        "reason_present": bool(reason),
        "approval_not_expired": current_time <= expires_at,
        "automatic_resume_disabled": request.get("automatic_resume") is not True,
    }

    approved = all(checks.values())

    if approved:
        state = "MANUAL_RESUME_APPROVED"
        action = "RESUME_RISK_MONITORING"
    else:
        state = "MANUAL_RESUME_BLOCKED"
        action = "KEEP_SYSTEM_PAUSED"

    return {
        "state": state,
        "approved": approved,
        "required_action": action,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "required_phrase": REQUIRED_PHRASE,
        "requested_by": requested_by,
        "reason": reason,
        "expires_at": expires_at.isoformat(),
        "evaluated_at": current_time.astimezone(timezone.utc).isoformat(),
        "pause_state_before": pause_state,
        "pause_required_before": pause_required,
        "kill_switch_active": kill_switch_active,
        "automatic_resume_allowed": False,
        "manual_resume_required": True,
        "risk_operations_allowed": approved,
    }
