from __future__ import annotations
from typing import Any

def build_cash_entries(
    simulation: dict[str, Any],
    lifecycle: dict[str, Any],
) -> list[dict[str, Any]]:
    entries = []
    initial_cash = float(simulation.get("initial_cash", 0.0))
    entries.append({
        "entry_type": "INITIAL_CASH",
        "amount": initial_cash,
        "source": "V95.01-V95.32",
    })
    for fill in simulation.get("fills", []):
        entries.append({
            "entry_type": "FILL_CASH_EFFECT",
            "amount": float(fill.get("cash_effect", 0.0)),
            "source": fill.get("fill_id"),
            "symbol": fill.get("symbol"),
        })
    for close in lifecycle.get("close_records", []):
        entries.append({
            "entry_type": "POSITION_CLOSE_PROCEEDS",
            "amount": float(close.get("gross_proceeds", 0.0))
                      - float(close.get("commission", 0.0)),
            "source": close.get("lifecycle_date"),
            "symbol": close.get("symbol"),
        })
    return entries

def build_position_entries(
    simulation: dict[str, Any],
    lifecycle: dict[str, Any],
) -> list[dict[str, Any]]:
    entries = []
    for fill in simulation.get("fills", []):
        if fill.get("state") not in {"FILLED", "PARTIALLY_FILLED"}:
            continue
        quantity = float(fill.get("filled_quantity", 0.0))
        if str(fill.get("side", "BUY")).upper() == "SELL":
            quantity = -quantity
        entries.append({
            "entry_type": "POSITION_FILL",
            "symbol": fill.get("symbol"),
            "quantity_delta": quantity,
            "source": fill.get("fill_id"),
        })
    for close in lifecycle.get("close_records", []):
        entries.append({
            "entry_type": "POSITION_CLOSE",
            "symbol": close.get("symbol"),
            "quantity_delta": -float(close.get("closed_quantity", 0.0)),
            "source": close.get("lifecycle_date"),
        })
    return entries

def aggregate_positions(entries: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for entry in entries:
        symbol = str(entry.get("symbol") or "")
        if not symbol:
            continue
        totals[symbol] = totals.get(symbol, 0.0) + float(
            entry.get("quantity_delta", 0.0)
        )
    return {
        symbol: round(quantity, 6)
        for symbol, quantity in totals.items()
    }
