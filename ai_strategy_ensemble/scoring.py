from __future__ import annotations
from typing import Any

def _f(value:Any)->float:
    try:return float(value)
    except Exception:return 0.0

def score(row:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    observations=int(row.get("observations",0) or 0)
    win_rate=_f(row.get("win_rate_pct"))
    profit_factor=_f(row.get("profit_factor"))
    sharpe=_f(row.get("sharpe"))
    drawdown=_f(row.get("maximum_drawdown_pct"))
    total_pnl=_f(row.get("total_pnl"))
    gross=max(0.0,min(100.0,
        win_rate*0.35+
        min(profit_factor,3.0)*15.0+
        max(-1.0,min(sharpe,3.0))*10.0+
        min(max(total_pnl,0.0)/100.0,15.0)
    ))
    penalty=drawdown*_f(policy.get("drawdown_penalty_factor",2.0))
    if total_pnl<0:
        penalty+=abs(total_pnl)/100.0*_f(policy.get("loss_penalty_factor",1.0))
    final=max(0.0,min(100.0,gross-penalty))
    eligible=observations>=int(policy["minimum_observations"]) and final>=_f(policy["minimum_score"])
    return {
        "strategy_id":row.get("strategy_id","UNKNOWN"),
        "observations":observations,
        "score":round(final,4),
        "eligible":eligible,
        "metrics":{
            "win_rate_pct":win_rate,
            "profit_factor":profit_factor,
            "sharpe":sharpe,
            "maximum_drawdown_pct":drawdown,
            "total_pnl":total_pnl,
        }
    }
