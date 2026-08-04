from __future__ import annotations
from typing import Any

from .schema import missing_keys


def _number(policy: dict[str, Any], name: str, minimum: float, maximum: float, errors: list[str]) -> float | None:
    try:
        value = float(policy.get(name))
    except (TypeError, ValueError):
        errors.append(f"{name.upper()}_INVALID")
        return None
    if not minimum <= value <= maximum:
        errors.append(f"{name.upper()}_OUT_OF_RANGE")
    return value


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    missing = missing_keys(policy)
    errors.extend(f"MISSING_{name.upper()}" for name in missing)

    checks = {
        "stage_valid": policy.get("stage") == "V391.01A",
        "mode_valid": policy.get("mode") == "RISK_GOVERNOR_POLICY_ONLY",
        "risk_governor_enabled": policy.get("risk_governor_enabled") is True,
        "paper_endpoint_only": policy.get("paper_endpoint_only") is True,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "kill_switch_required": policy.get("kill_switch_required") is True,
        "manual_resume_required": policy.get("manual_resume_required") is True,
        "automatic_resume_disabled": policy.get("automatic_resume_enabled") is False,
    }

    for name, passed in checks.items():
        if not passed:
            errors.append(name.upper())

    _number(policy, "daily_loss_limit_pct", 0.001, 0.05, errors)
    _number(policy, "maximum_drawdown_pct", 0.001, 0.20, errors)
    _number(policy, "maximum_position_pct", 0.001, 0.25, errors)
    _number(policy, "maximum_total_exposure_pct", 0.01, 1.00, errors)
    _number(policy, "maximum_symbol_exposure_pct", 0.001, 0.25, errors)

    try:
        maximum_losses = int(policy.get("maximum_consecutive_losses"))
        if not 1 <= maximum_losses <= 10:
            errors.append("MAXIMUM_CONSECUTIVE_LOSSES_OUT_OF_RANGE")
    except (TypeError, ValueError):
        errors.append("MAXIMUM_CONSECUTIVE_LOSSES_INVALID")

    if bool(policy.get("kill_switch_active")) and bool(policy.get("risk_operations_allowed", True)):
        errors.append("KILL_SWITCH_MUST_DISABLE_RISK_OPERATIONS")

    if float(policy.get("maximum_symbol_exposure_pct", 1.0)) > float(policy.get("maximum_position_pct", 0.0)):
        errors.append("SYMBOL_EXPOSURE_EXCEEDS_POSITION_LIMIT")

    unique_errors = sorted(set(errors))
    return {
        "valid": not unique_errors,
        "checks": checks,
        "errors": unique_errors,
        "missing_keys": missing,
    }
