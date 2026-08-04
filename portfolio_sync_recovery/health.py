from __future__ import annotations


def classify(
    account: dict,
    account_drifts: list[dict],
    position_drifts: list[dict],
    open_orders: list[dict],
    policy: dict,
) -> dict:
    issues: list[str] = []

    if account.get("status") != "ACTIVE":
        issues.append("ACCOUNT_NOT_ACTIVE")
    if account.get("account_blocked"):
        issues.append("ACCOUNT_BLOCKED")
    if account.get("trading_blocked"):
        issues.append("TRADING_BLOCKED")

    missing_positions = [x for x in position_drifts if x.get("type") == "POSITION_MISSING"]
    if missing_positions:
        issues.append("POSITION_MISSING_DETECTED")

    if len(account_drifts) > int(policy.get("maximum_account_drift_events", 4)):
        issues.append("ACCOUNT_DRIFT_LIMIT_EXCEEDED")
    if len(position_drifts) > int(policy.get("maximum_position_drift_events", 10)):
        issues.append("POSITION_DRIFT_LIMIT_EXCEEDED")
    if len(open_orders) > int(policy.get("maximum_open_orders", 5)):
        issues.append("OPEN_ORDER_LIMIT_EXCEEDED")

    if any(issue in {"ACCOUNT_NOT_ACTIVE", "ACCOUNT_BLOCKED", "TRADING_BLOCKED"} for issue in issues):
        health = "CRITICAL"
    elif issues:
        health = "WARNING"
    else:
        health = "HEALTHY"

    return {
        "health": health,
        "issues": issues,
        "recovery_required": health != "HEALTHY",
    }
