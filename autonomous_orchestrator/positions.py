from __future__ import annotations
from typing import Any

def apply(fills:list[dict[str,Any]])->list[dict[str,Any]]:
    positions=[]
    for f in fills:
        qty=float(f.get("qty",0))
        signed=qty if f.get("side")=="buy" else -qty
        positions.append({
            "symbol":f.get("symbol"),
            "quantity":signed,
            "average_price":f.get("fill_price"),
            "market_value":round(signed*float(f.get("fill_price",0)),2),
        })
    return positions
