from __future__ import annotations
from typing import Any

def reconcile(local_positions: list[dict[str, Any]], broker_positions: list[dict[str, Any]]) -> dict[str, Any]:
    def index(rows: list[dict[str, Any]]) -> dict[str, float]:
        result = {}
        for row in rows:
            result[str(row.get("symbol", "")).upper()] = float(row.get("quantity", 0) or 0)
        return result

    local = index(local_positions)
    broker = index(broker_positions)
    symbols = sorted(set(local) | set(broker))
    rows = []
    for symbol in symbols:
        local_qty = local.get(symbol, 0.0)
        broker_qty = broker.get(symbol, 0.0)
        rows.append({
            "symbol": symbol,
            "local_quantity": local_qty,
            "broker_quantity": broker_qty,
            "matched": local_qty == broker_qty,
        })
    conflicts = [row for row in rows if not row["matched"]]
    return {
        "passed": not conflicts,
        "conflict_count": len(conflicts),
        "rows": rows,
    }
