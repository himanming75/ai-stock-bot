from __future__ import annotations
from typing import Any

def _price(snapshot: dict[str,Any]) -> float:
    trade=snapshot.get("latestTrade") or snapshot.get("latest_trade") or {}
    return float(trade.get("p",0.0) or 0.0)

def build_signals(
    snapshots: dict[str,Any],
    policy: dict[str,Any],
) -> list[dict[str,Any]]:
    rows=[]
    for symbol in policy.get("symbols",[]):
        snap=snapshots.get(symbol,{})
        price=_price(snap)
        reference=float(policy.get("reference_prices",{}).get(symbol,price or 1))
        change_pct=(price/reference-1)*100 if reference else 0.0
        threshold=float(policy.get("signal_threshold_pct",0.25))
        if change_pct>=threshold: action="BUY"
        elif change_pct<=-threshold: action="SELL"
        else: action="HOLD"
        rows.append({
            "symbol":symbol,
            "price":round(price,4),
            "reference_price":round(reference,4),
            "change_pct":round(change_pct,6),
            "action":action,
            "strategy_id":"SNAPSHOT_MOMENTUM_SHADOW",
        })
    return rows
