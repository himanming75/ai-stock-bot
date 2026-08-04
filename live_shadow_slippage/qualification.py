from __future__ import annotations
from typing import Any

def evaluate(policy: dict[str, Any], signal: dict[str, Any], account: dict[str, Any], quote: dict[str, Any], slippage: dict[str, Any]) -> dict[str, Any]:
    quantity = int(signal.get("quantity", 1) or 1)
    notional = quantity * float(slippage["expected_live_fill_price"])
    buying_power = float(account.get("buying_power", 0) or 0)
    required_power = notional * (1 + float(policy["minimum_buying_power_buffer_pct"]) / 100)
    checks = {
        "market_open": quote["market_open"] is True,
        "quote_fresh": quote["quote_age_seconds"] <= float(policy["maximum_quote_age_seconds"]),
        "spread_within_limit": quote["spread_pct"] <= float(policy["maximum_spread_pct"]),
        "slippage_within_limit": abs(float(slippage["slippage_pct"])) <= float(policy["maximum_slippage_pct"]),
        "buying_power_sufficient": buying_power >= required_power,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    score_weights = {
        "market_open": 15,
        "quote_fresh": 15,
        "spread_within_limit": 20,
        "slippage_within_limit": 25,
        "buying_power_sufficient": 25,
    }
    score = sum(weight for name, weight in score_weights.items() if checks[name])
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": score >= float(policy["minimum_qualification_score"]) and not failed,
        "score": float(score),
        "minimum_score": float(policy["minimum_qualification_score"]),
        "checks": checks,
        "failed": failed,
        "expected_notional": round(notional, 2),
        "required_buying_power": round(required_power, 2),
        "available_buying_power": round(buying_power, 2),
    }
