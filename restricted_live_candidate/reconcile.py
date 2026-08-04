from __future__ import annotations
from typing import Any

def compare(
    paper_candidates:list[dict[str,Any]],
    live_positions:list[dict[str,Any]],
    live_orders:list[dict[str,Any]],
)->dict[str,Any]:
    live_position_symbols={p.get("symbol") for p in live_positions}
    live_order_symbols={o.get("symbol") for o in live_orders}
    rows=[]
    for c in paper_candidates:
        symbol=c.get("symbol")
        rows.append({
            "candidate_id":c.get("candidate_id"),
            "symbol":symbol,
            "live_position_exists":symbol in live_position_symbols,
            "live_order_exists":symbol in live_order_symbols,
            "conflict_detected":symbol in live_position_symbols or symbol in live_order_symbols,
        })
    return {
        "rows":rows,
        "conflict_count":sum(1 for r in rows if r["conflict_detected"]),
        "passed":all(not r["conflict_detected"] for r in rows),
    }
