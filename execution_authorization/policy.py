from __future__ import annotations
from typing import Any


REQUIRED_KEYS = {
    "stage",
    "mode",
    "authorization_required",
    "paper_endpoint_only",
    "live_submission_enabled",
    "broker_write_enabled",
    "manual_approval_required",
    "authorization_token_ttl_seconds",
}


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_KEYS - set(policy))
    errors = [f"MISSING_{name.upper()}" for name in missing]

    checks = {
        "stage_valid": policy.get("stage") == "V392.01A",
        "mode_valid": policy.get("mode") == "EXECUTION_AUTHORIZATION_FOUNDATION",
        "authorization_required": policy.get("authorization_required") is True,
        "paper_endpoint_only": policy.get("paper_endpoint_only") is True,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "manual_approval_required": policy.get("manual_approval_required") is True,
        "automatic_authorization_disabled": (
            policy.get("automatic_authorization_enabled") is False
        ),
    }

    for name, passed in checks.items():
        if not passed:
            errors.append(name.upper())

    try:
        ttl = int(policy.get("authorization_token_ttl_seconds"))
        if not 30 <= ttl <= 3600:
            errors.append("AUTHORIZATION_TOKEN_TTL_SECONDS_OUT_OF_RANGE")
    except (TypeError, ValueError):
        errors.append("AUTHORIZATION_TOKEN_TTL_SECONDS_INVALID")

    errors = sorted(set(errors))
    return {
        "valid": not errors,
        "checks": checks,
        "errors": errors,
        "missing_keys": missing,
    }
