from __future__ import annotations
from typing import Any

def open_positions(fills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows=[]
    for fill in fills:
        qty=int(fill.get("filled_quantity",0))
        if qty<=0:
            continue
        price=float(fill.get("fill_price",0.0))
        rows.append({
            "strategy_id":fill.get("strategy_id"),
            "symbol":fill.get("symbol"),
            "quantity":qty,
            "average_cost":price,
            "entry_value":round(qty*price,2),
            "highest_price":price,
            "state":"OPEN",
            "realized_pnl":0.0,
        })
    return rows

def merge_positions(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lookup={}
    for row in existing+incoming:
        key=(row.get("strategy_id"),row.get("symbol"))
        if key not in lookup:
            lookup[key]=dict(row)
            continue
        current=lookup[key]
        q1=int(current.get("quantity",0))
        q2=int(row.get("quantity",0))
        total=q1+q2
        if total>0:
            current["average_cost"]=round(
                (
                    q1*float(current.get("average_cost",0.0))
                    +q2*float(row.get("average_cost",0.0))
                )/total,
                4,
            )
        current["quantity"]=total
        current["entry_value"]=round(
            total*float(current.get("average_cost",0.0)),2
        )
    return list(lookup.values())
