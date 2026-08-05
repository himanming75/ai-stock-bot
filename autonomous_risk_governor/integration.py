from __future__ import annotations
from typing import Any


EXPECTED_STAGES = {
    "policy": "V391.01A",
    "daily_loss": "V391.02A",
    "drawdown": "V391.03A",
    "position": "V391.04A",
    "exposure": "V391.05A",
    "concentration": "V391.06A",
    "kill_switch": "V391.07A",
    "auto_pause": "V391.08A",
    "manual_resume": "V391.09A",
}


WARNING_STATES = {
    "DAILY_LOSS_GUARD_WARNING",
    "MAX_DRAWDOWN_GUARD_WARNING",
    "POSITION_SIZE_GUARD_WARNING",
    "TOTAL_EXPOSURE_GUARD_WARNING",
    "SYMBOL_CONCENTRATION_GUARD_WARNING",
    "AUTO_PAUSE_GUARD_WARNING",
}


BLOCKING_STATES = {
    "RISK_POLICY_BLOCKED",
    "DAILY_LOSS_GUARD_PAUSE_REQUIRED",
    "MAX_DRAWDOWN_GUARD_PAUSE_REQUIRED",
    "POSITION_SIZE_GUARD_BLOCKED",
    "TOTAL_EXPOSURE_GUARD_BLOCKED",
    "SYMBOL_CONCENTRATION_GUARD_BLOCKED",
    "KILL_SWITCH_GUARD_BLOCKED",
    "KILL_SWITCH_GUARD_INVALID",
    "AUTO_PAUSE_GUARD_PAUSED",
    "MANUAL_RESUME_GUARD_BLOCKED",
}


def evaluate_integration(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    missing: list[str] = []
    invalid: list[dict[str, str]] = []
    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    policy_hashes: set[str] = set()

    for name, expected_stage in EXPECTED_STAGES.items():
        result = results.get(name)
        if not isinstance(result, dict):
            missing.append(name)
            continue

        stage = str(result.get("stage", ""))
        status = str(result.get("status", ""))
        state = str(result.get("state", ""))
        policy_hash = result.get("policy_hash")

        if name == "policy":
            stage = str(result.get("stage", ""))
            status = str(result.get("status", ""))
            state = str(result.get("state", ""))

        if stage != expected_stage:
            invalid.append({
                "source": name,
                "reason": "STAGE_MISMATCH",
                "value": stage,
            })

        if status != "PASS":
            invalid.append({
                "source": name,
                "reason": "STATUS_NOT_PASS",
                "value": status,
            })

        if isinstance(policy_hash, str) and policy_hash:
            policy_hashes.add(policy_hash)

        if state in BLOCKING_STATES:
            blocking.append({
                "source": name,
                "state": state,
                "reason": "BLOCKING_STATE",
            })
        elif state in WARNING_STATES:
            warnings.append({
                "source": name,
                "state": state,
                "reason": "WARNING_STATE",
            })

        if result.get("risk_operations_allowed") is False:
            if name not in {"auto_pause", "manual_resume"} or state not in {
                "AUTO_PAUSE_GUARD_STANDBY",
                "MANUAL_RESUME_GUARD_APPROVED",
            }:
                blocking.append({
                    "source": name,
                    "state": state,
                    "reason": "RISK_OPERATIONS_NOT_ALLOWED",
                })

    policy_hash_consistent = len(policy_hashes) <= 1
    if not policy_hash_consistent:
        invalid.append({
            "source": "integration",
            "reason": "POLICY_HASH_MISMATCH",
            "value": ",".join(sorted(policy_hashes)),
        })

    blocked = bool(missing or invalid or blocking)
    warning = bool(warnings) and not blocked

    if blocked:
        decision = "BLOCKED"
        state = "RISK_GOVERNOR_INTEGRATION_BLOCKED"
        action = "DO_NOT_AUTHORIZE_EXECUTION"
    elif warning:
        decision = "WARN"
        state = "RISK_GOVERNOR_INTEGRATION_WARNING"
        action = "REQUIRE_MANUAL_REVIEW"
    else:
        decision = "ALLOW"
        state = "RISK_GOVERNOR_INTEGRATION_READY"
        action = "ALLOW_NEXT_AUTHORIZATION_STAGE"

    return {
        "decision": decision,
        "state": state,
        "required_action": action,
        "missing_sources": missing,
        "invalid_sources": invalid,
        "blocking_sources": blocking,
        "warning_sources": warnings,
        "policy_hash_consistent": policy_hash_consistent,
        "risk_operations_allowed": decision == "ALLOW",
        "execution_authorization_allowed": False,
        "automatic_resume_allowed": False,
        "manual_review_required": decision in {"WARN", "BLOCKED"},
    }
