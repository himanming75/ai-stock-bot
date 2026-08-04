from __future__ import annotations
from typing import Any

def summarize(starting_equity:float,positions:list[dict[str,Any]])->dict[str,Any]:
    market_value=sum(float(p.get("market_value",0)) for p in positions)
    ending_equity=starting_equity
    return {
        "starting_equity":round(starting_equity,2),
        "ending_equity":round(ending_equity,2),
        "open_market_value":round(market_value,2),
        "realized_pnl":0.0,
        "unrealized_pnl":0.0,
        "total_pnl":0.0,
        "daily_return_pct":0.0,
    }
