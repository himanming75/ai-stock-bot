from __future__ import annotations
import math, statistics
from v89_engine.strategies import signal

def max_drawdown(curve):
    peak=curve[0] if curve else 0; worst=0
    for x in curve:
        peak=max(peak,x)
        if peak: worst=min(worst,(x-peak)/peak)
    return abs(worst)*100

def run_strategy(bars, strategy, config, initial_cash=100000, cost_bps=3):
    cash=float(initial_cash); qty=0.0; entry=0.0; trades=[]; curve=[]; closes=[]
    for bar in bars:
        closes.append(bar["close"]); action=signal(strategy,closes,config)
        price=bar["close"]; cost=cost_bps/10000
        if action=="BUY" and qty==0:
            fill=price*(1+cost); qty=(cash*0.95)/fill; entry=fill; cash-=qty*fill
        elif action=="SELL" and qty>0:
            fill=price*(1-cost); proceeds=qty*fill; pnl=(fill-entry)*qty
            trades.append(pnl); cash+=proceeds; qty=0
        curve.append(cash+qty*price)
    if qty>0:
        fill=bars[-1]["close"]*(1-cost); pnl=(fill-entry)*qty
        trades.append(pnl); cash+=qty*fill; qty=0; curve[-1]=cash
    returns=[(b-a)/a for a,b in zip(curve,curve[1:]) if a]
    sharpe=(statistics.mean(returns)/statistics.pstdev(returns)*math.sqrt(252)
            if len(returns)>1 and statistics.pstdev(returns)>0 else 0)
    wins=[x for x in trades if x>0]; losses=[x for x in trades if x<0]
    pf=sum(wins)/abs(sum(losses)) if losses else (999.0 if wins else 0.0)
    total_return=(curve[-1]/initial_cash-1)*100 if curve else 0
    return {
        "strategy":strategy,"total_return_pct":round(total_return,4),
        "maximum_drawdown_pct":round(max_drawdown(curve),4),
        "sharpe_ratio":round(sharpe,4),"total_trades":len(trades),
        "win_rate_pct":round(len(wins)/len(trades)*100,4) if trades else 0,
        "profit_factor":round(pf,4),"ending_equity":round(curve[-1],4) if curve else initial_cash,
        "equity_curve":[round(x,4) for x in curve]
    }

def buy_hold(bars, initial_cash=100000):
    ret=(bars[-1]["close"]/bars[0]["close"]-1)*100 if bars else 0
    return {"strategy":"BUY_AND_HOLD","total_return_pct":round(ret,4),
            "maximum_drawdown_pct":round(max_drawdown([initial_cash*b["close"]/bars[0]["close"] for b in bars]),4),
            "sharpe_ratio":0.0,"total_trades":1,"win_rate_pct":100.0 if ret>0 else 0.0,
            "profit_factor":999.0 if ret>0 else 0.0,"ending_equity":round(initial_cash*(1+ret/100),4)}
