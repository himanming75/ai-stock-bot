from __future__ import annotations

PLANS = {
    "FREE": {
        "monthly_price_usd": 0,
        "workspace_limit": 1,
        "broker_limit": 1,
        "ai_requests_per_day": 20,
        "backtests_per_month": 3,
        "api_access": False,
        "paper_runtime_hours_per_month": 20,
    },
    "BASIC": {
        "monthly_price_usd": 29,
        "workspace_limit": 2,
        "broker_limit": 2,
        "ai_requests_per_day": 100,
        "backtests_per_month": 20,
        "api_access": False,
        "paper_runtime_hours_per_month": 100,
    },
    "PRO": {
        "monthly_price_usd": 99,
        "workspace_limit": 10,
        "broker_limit": 10,
        "ai_requests_per_day": 1000,
        "backtests_per_month": 200,
        "api_access": True,
        "paper_runtime_hours_per_month": 1000,
    },
    "ENTERPRISE": {
        "monthly_price_usd": 499,
        "workspace_limit": 100,
        "broker_limit": 100,
        "ai_requests_per_day": 100000,
        "backtests_per_month": 10000,
        "api_access": True,
        "paper_runtime_hours_per_month": 100000,
    },
}


def get_plan(name: str) -> dict:
    normalized = name.upper()
    if normalized not in PLANS:
        raise ValueError("INVALID_PLAN")
    return dict(PLANS[normalized])


def feature_enabled(
    *,
    plan: str,
    feature: str,
) -> bool:
    item = get_plan(plan)
    if feature == "api_access":
        return bool(item["api_access"])
    if feature in {
        "workspace_limit",
        "broker_limit",
        "ai_requests_per_day",
        "backtests_per_month",
        "paper_runtime_hours_per_month",
    }:
        return item[feature] > 0
    return False
