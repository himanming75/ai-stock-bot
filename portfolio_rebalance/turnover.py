from __future__ import annotations
from typing import Any

def apply_turnover_limit(
    intents: list[dict[str, Any]],
    account_equity: float,
    cash: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    maximum_turnover_pct = float(policy.get("maximum_turnover_pct", 25.0))
    minimum_cash_pct = float(policy.get("minimum_projected_cash_pct", 10.0))
    maximum_total_notional = account_equity * maximum_turnover_pct / 100.0
    required_cash = account_equity * minimum_cash_pct / 100.0
    remaining_turnover = maximum_total_notional

    accepted = []
    limited = []

    # Execute planned sells first because they increase available cash.
    sells = sorted(
        [row for row in intents if row.get("side") == "SELL"],
        key=lambda row: abs(float(row.get("weight_gap_pct", 0.0))),
        reverse=True,
    )
    buys = sorted(
        [row for row in intents if row.get("side") == "BUY"],
        key=lambda row: abs(float(row.get("weight_gap_pct", 0.0))),
        reverse=True,
    )

    accepted_sell_notional = 0.0
    for row in sells:
        requested = float(row.get("planned_notional", 0.0))
        accepted_notional = min(requested, remaining_turnover)
        item = dict(row)
        if accepted_notional <= 1e-9:
            item["state"] = "LIMITED_TURNOVER"
            item["planned_notional"] = 0.0
            item["quantity"] = 0.0
            limited.append(item)
        elif accepted_notional < requested - 1e-9:
            item["state"] = "PARTIALLY_LIMITED_TURNOVER"
            ratio = accepted_notional / requested
            item["planned_notional"] = round(accepted_notional, 6)
            item["quantity"] = round(float(item["quantity"]) * ratio, 6)
            limited.append(item)
        else:
            accepted.append(item)
        accepted_sell_notional += accepted_notional
        remaining_turnover -= accepted_notional

    available_buy_cash = max(
        0.0,
        cash + accepted_sell_notional - required_cash,
    )

    accepted_buy_notional = 0.0
    for row in buys:
        requested = float(row.get("planned_notional", 0.0))
        capacity = min(remaining_turnover, available_buy_cash)
        accepted_notional = min(requested, capacity)
        item = dict(row)
        if accepted_notional <= 1e-9:
            item["state"] = (
                "LIMITED_CASH_RESERVE"
                if available_buy_cash <= 1e-9
                else "LIMITED_TURNOVER"
            )
            item["planned_notional"] = 0.0
            item["quantity"] = 0.0
            limited.append(item)
        elif accepted_notional < requested - 1e-9:
            item["state"] = "PARTIALLY_LIMITED_CASH_OR_TURNOVER"
            ratio = accepted_notional / requested
            item["planned_notional"] = round(accepted_notional, 6)
            item["quantity"] = round(float(item["quantity"]) * ratio, 6)
            limited.append(item)
        else:
            accepted.append(item)
        accepted_buy_notional += accepted_notional
        remaining_turnover -= accepted_notional
        available_buy_cash -= accepted_notional

    combined = accepted + limited
    used = accepted_sell_notional + accepted_buy_notional
    projected_cash = cash + accepted_sell_notional - accepted_buy_notional

    return {
        "maximum_turnover_pct": maximum_turnover_pct,
        "maximum_total_notional": round(maximum_total_notional, 6),
        "minimum_projected_cash_pct": minimum_cash_pct,
        "required_cash": round(required_cash, 6),
        "accepted_sell_notional": round(accepted_sell_notional, 6),
        "accepted_buy_notional": round(accepted_buy_notional, 6),
        "projected_cash_after_limits": round(projected_cash, 6),
        "projected_cash_pct_after_limits": round(
            projected_cash / account_equity * 100.0
            if account_equity else 0.0,
            6,
        ),
        "used_total_notional": round(used, 6),
        "used_turnover_pct": round(
            used / account_equity * 100.0 if account_equity else 0.0,
            6,
        ),
        "intents": combined,
    }
