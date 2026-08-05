from __future__ import annotations
from typing import Any


def evaluate_kill_switch(
    kill_switch_required: Any,
    kill_switch_active: Any,
    manual_resume_required: Any,
    automatic_resume_enabled: Any,
    risk_operations_allowed: Any,
) -> dict:
    required = bool(kill_switch_required)
    active = bool(kill_switch_active)
    manual_resume = bool(manual_resume_required)
    automatic_resume = bool(automatic_resume_enabled)
    operations_allowed = bool(risk_operations_allowed)

    errors: list[str] = []

    if not required:
        errors.append("KILL_SWITCH_NOT_REQUIRED")
    if not manual_resume:
        errors.append("MANUAL_RESUME_NOT_REQUIRED")
    if automatic_resume:
        errors.append("AUTOMATIC_RESUME_MUST_BE_DISABLED")
    if active and operations_allowed:
        errors.append("ACTIVE_KILL_SWITCH_WITH_RISK_OPERATIONS_ALLOWED")

    valid = len(errors) == 0

    if not valid:
        state = "KILL_SWITCH_POLICY_INVALID"
        action = "BLOCK_ALL_RISK_OPERATIONS"
        effective_operations_allowed = False
    elif active:
        state = "KILL_SWITCH_ACTIVE"
        action = "BLOCK_ALL_RISK_OPERATIONS"
        effective_operations_allowed = False
    else:
        state = "KILL_SWITCH_STANDBY"
        action = "CONTINUE_MONITORING"
        effective_operations_allowed = operations_allowed

    return {
        "valid": valid,
        "errors": errors,
        "kill_switch_required": required,
        "kill_switch_active": active,
        "manual_resume_required": manual_resume,
        "automatic_resume_enabled": automatic_resume,
        "requested_risk_operations_allowed": operations_allowed,
        "effective_risk_operations_allowed": effective_operations_allowed,
        "state": state,
        "required_action": action,
        "pause_required": active or not valid,
        "resume_allowed": False if active else valid and manual_resume,
    }
