from __future__ import annotations
from typing import Any

FINAL_STATES = {"filled", "canceled", "expired", "rejected", "replaced"}

def calculate(account: dict[str, Any], positions: list[dict[str, Any]], orders: list[dict[str, Any]]) -> dict[str, Any]:
    equity = float(account.get("equity", 0) or 0)
    last_equity = float(account.get("last_equity", equity) or equity)
    daily_pnl = equity - last_equity
    daily_return_pct = daily_pnl / last_equity * 100 if last_equity else 0.0
    unrealized = sum(float(row.get("unrealized_pl", 0) or 0) for row in positions)
    order_states: dict[str, int] = {}
    for row in orders:
        status = str(row.get("status", "unknown")).lower()
        order_states[status] = order_states.get(status, 0) + 1
    return {
        "equity": round(equity, 2),
        "last_equity": round(last_equity, 2),
        "daily_pnl": round(daily_pnl, 2),
        "daily_return_pct": round(daily_return_pct, 6),
        "unrealized_pl": round(unrealized, 2),
        "position_count": len(positions),
        "order_count": len(orders),
        "order_states": order_states,
        "final_order_count": sum(
            count for state, count in order_states.items() if state in FINAL_STATES
        ),
    }
