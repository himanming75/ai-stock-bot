from __future__ import annotations


def build_plan(health: dict, account_drifts: list[dict], position_drifts: list[dict]) -> list[dict]:
    actions: list[dict] = []

    for issue in health.get("issues", []):
        if issue in {"ACCOUNT_NOT_ACTIVE", "ACCOUNT_BLOCKED", "TRADING_BLOCKED"}:
            actions.append({
                "action": "PAUSE_AUTOMATION",
                "reason": issue,
                "automatic_execution_allowed": False,
            })
        elif issue == "POSITION_MISSING_DETECTED":
            actions.append({
                "action": "REFRESH_ORDER_AND_POSITION_HISTORY",
                "reason": issue,
                "automatic_execution_allowed": False,
            })
        elif issue in {"ACCOUNT_DRIFT_LIMIT_EXCEEDED", "POSITION_DRIFT_LIMIT_EXCEEDED"}:
            actions.append({
                "action": "REBUILD_INTERNAL_PORTFOLIO_SNAPSHOT",
                "reason": issue,
                "automatic_execution_allowed": False,
            })

    if account_drifts and not any(x["action"] == "REBUILD_INTERNAL_PORTFOLIO_SNAPSHOT" for x in actions):
        actions.append({
            "action": "REVIEW_ACCOUNT_DRIFT",
            "reason": "ACCOUNT_VALUE_CHANGED",
            "automatic_execution_allowed": False,
        })

    if position_drifts and not any(x["action"] == "REBUILD_INTERNAL_PORTFOLIO_SNAPSHOT" for x in actions):
        actions.append({
            "action": "REVIEW_POSITION_DRIFT",
            "reason": "POSITION_STATE_CHANGED",
            "automatic_execution_allowed": False,
        })

    return actions
