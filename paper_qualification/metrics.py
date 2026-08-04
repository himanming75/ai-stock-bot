from __future__ import annotations
import math
from typing import Any

def _f(v:Any)->float:
    try:return float(v)
    except Exception:return 0.0

def compute(trades:list[dict[str,Any]],daily:list[dict[str,Any]])->dict[str,Any]:
    pnls=[_f(t.get("realized_pnl",t.get("pnl",0))) for t in trades]
    wins=[x for x in pnls if x>0]
    losses=[x for x in pnls if x<0]
    gross_profit=sum(wins)
    gross_loss=abs(sum(losses))
    profit_factor=(gross_profit/gross_loss) if gross_loss>0 else (999.0 if gross_profit>0 else 0.0)
    win_rate=(len(wins)/len(pnls)*100.0) if pnls else 0.0
    avg_pnl=(sum(pnls)/len(pnls)) if pnls else 0.0
    returns=[_f(x.get("daily_return_pct",0))/100.0 for x in daily]
    sharpe=0.0
    if len(returns)>=2:
        mean=sum(returns)/len(returns)
        variance=sum((x-mean)**2 for x in returns)/(len(returns)-1)
        std=math.sqrt(variance)
        if std>0: sharpe=(mean/std)*math.sqrt(252)
    equities=[_f(x.get("ending_equity",0)) for x in daily if _f(x.get("ending_equity",0))>0]
    peak=0.0;max_dd=0.0
    for eq in equities:
        peak=max(peak,eq)
        if peak>0:max_dd=max(max_dd,(peak-eq)/peak*100.0)
    dates={str(x.get("session_date",x.get("date",""))) for x in daily if x.get("session_date") or x.get("date")}
    return {
        "trading_days":len(dates) or len(daily),
        "closed_trades":len(pnls),
        "win_count":len(wins),
        "loss_count":len(losses),
        "win_rate_pct":round(win_rate,4),
        "gross_profit":round(gross_profit,2),
        "gross_loss":round(gross_loss,2),
        "profit_factor":round(profit_factor,4),
        "average_trade_pnl":round(avg_pnl,4),
        "total_realized_pnl":round(sum(pnls),2),
        "sharpe":round(sharpe,4),
        "maximum_drawdown_pct":round(max_dd,4),
    }
