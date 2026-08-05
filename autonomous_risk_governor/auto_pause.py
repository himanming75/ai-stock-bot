from __future__ import annotations
from typing import Any


BLOCKING_STATES = {
    "DAILY_LOSS_GUARD_PAUSE_REQUIRED",
    "MAX_DRAWDOWN_GUARD_PAUSE_REQUIRED",
    "POSITION_SIZE_GUARD_BLOCKED",
    "TOTAL_EXPOSURE_GUARD_BLOCKED",
    "SYMBOL_CONCENTRATION_GUARD_BLOCKED",
    "KILL_SWITCH_GUARD_BLOCKED",
    "KILL_SWITCH_GUARD_INVALID",
}


WARNING_STATES = {
    "DAILY_LOSS_GUARD_WARNING",
    "MAX_DRAWDOWN_GUARD_WARNING",
    "POSITION_SIZE_GUARD_WARNING",
    "TOTAL_EXPOSURE_GUARD_WARNING",
    "SYMBOL_CONCENTRATION_GUARD_WARNING",
}


def evaluate_auto_pause(guard_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blocking_sources: list[dict[str, str]] = []
    warning_sources: list[dict[str, str]] = []
    invalid_sources: list[dict[str, str]] = []

    for name, result in guard_results.items():
        state = str(result.get("state", ""))
        status = str(result.get("status", ""))

        if status != "PASS":
            invalid_sources.append({
                "source": name,
                "state": state or "UNKNOWN",
                "reason": "GUARD_STATUS_NOT_PASS",
            })
            continue

        if state in BLOCKING_STATES:
            blocking_sources.append({
                "source": name,
                "state": state,
                "reason": "BLOCKING_GUARD_STATE",
            })
        elif state in WARNING_STATES:
            warning_sources.append({
                "source": name,
                "state": state,
                "reason": "WARNING_GUARD_STATE",
            })

        if result.get("risk_operations_allowed") is False:
            blocking_sources.append({
                "source": name,
                "state": state,
                "reason": "RISK_OPERATIONS_NOT_ALLOWED",
            })

    pause_required = bool(blocking_sources or invalid_sources)
    warning = bool(warning_sources) and not pause_required

    if pause_required:
        state = "AUTO_PAUSE_REQUIRED"
        action = "PAUSE_ALL_NEW_RISK"
    elif warning:
        state = "AUTO_PAUSE_WARNING"
        action = "CONTINUE_WITH_MANUAL_REVIEW"
    else:
        state = "AUTO_PAUSE_STANDBY"
        action = "CONTINUE_MONITORING"

    return {
        "state": state,
        "required_action": action,
        "pause_required": pause_required,
        "warning": warning,
        "blocking_sources": blocking_sources,
        "warning_sources": warning_sources,
        "invalid_sources": invalid_sources,
        "risk_operations_allowed": not pause_required,
        "automatic_resume_allowed": False,
        "manual_resume_required": pause_required,
    }
