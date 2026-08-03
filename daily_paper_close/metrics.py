from __future__ import annotations
from typing import Any

def daily_metrics(
    starting_equity: float,
    ending_equity: float,
    realized_pnl: float,
    unrealized_pnl: float,
) -> dict[str, Any]:
    daily_pnl = ending_equity - starting_equity
    daily_return_pct = (
        daily_pnl / starting_equity * 100.0
        if starting_equity else 0.0
    )
    return {
        "starting_equity": round(starting_equity, 4),
        "ending_equity": round(ending_equity, 4),
        "daily_pnl": round(daily_pnl, 4),
        "daily_return_pct": round(daily_return_pct, 6),
        "realized_pnl": round(realized_pnl, 4),
        "unrealized_pnl": round(unrealized_pnl, 4),
        "total_pnl": round(realized_pnl + unrealized_pnl, 4),
    }

def fill_summary(simulation: dict[str, Any]) -> dict[str, Any]:
    fills = simulation.get("fills", [])
    return {
        "fill_count": len(fills),
        "filled_count": sum(1 for x in fills if x.get("state") == "FILLED"),
        "partial_fill_count": sum(
            1 for x in fills if x.get("state") == "PARTIALLY_FILLED"
        ),
        "not_filled_count": sum(
            1 for x in fills if x.get("state") == "NOT_FILLED"
        ),
        "gross_notional": round(
            sum(float(x.get("gross_notional", 0.0)) for x in fills), 4
        ),
        "commission": round(
            sum(float(x.get("commission", 0.0)) for x in fills), 4
        ),
    }

def position_summary(account: dict[str, Any]) -> dict[str, Any]:
    positions = account.get("reported_positions", {})
    rows = []
    for symbol, value in sorted(positions.items()):
        if not isinstance(value, dict):
            continue
        rows.append({
            "symbol": symbol,
            "quantity": float(value.get("quantity", 0.0)),
            "average_cost": float(value.get("average_cost", 0.0)),
            "holding_days": int(value.get("holding_days", 0)),
            "status": value.get("status", "OPEN"),
        })
    return {
        "open_position_count": len(rows),
        "positions": rows,
    }
