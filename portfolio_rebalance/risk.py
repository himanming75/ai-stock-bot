from __future__ import annotations
from typing import Any

def evaluate_rebalance_risk(
    intents: list[dict[str, Any]],
    target_cash_pct: float,
    account_equity: float,
    cash: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    buy_notional = sum(
        float(row.get("planned_notional", 0.0))
        for row in intents
        if row.get("side") == "BUY"
    )
    sell_notional = sum(
        float(row.get("planned_notional", 0.0))
        for row in intents
        if row.get("side") == "SELL"
    )
    projected_cash = cash - buy_notional + sell_notional
    projected_cash_pct = (
        projected_cash / account_equity * 100.0 if account_equity else 0.0
    )
    minimum_cash_pct = float(
        policy.get("minimum_projected_cash_pct", target_cash_pct)
    )
    maximum_intents = int(policy.get("maximum_intent_count", 10))
    checks = {
        "intent_count_limit": len(intents) <= maximum_intents,
        "projected_cash_nonnegative": projected_cash >= -0.01,
        "minimum_projected_cash": projected_cash_pct >= minimum_cash_pct - 1e-6,
        "all_submission_disabled": all(
            row.get("submission_allowed") is False for row in intents
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
        "buy_notional": round(buy_notional, 6),
        "sell_notional": round(sell_notional, 6),
        "projected_cash": round(projected_cash, 6),
        "projected_cash_pct": round(projected_cash_pct, 6),
    }
