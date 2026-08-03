from __future__ import annotations
from pathlib import Path
from v89_engine.io import load_bars, load_json, write_json
from v89_engine.discovery import discover_historical_files
from v89_engine.backtest import run_strategy, buy_hold
from v89_engine.gates import evaluate
from v89_engine.final_validation import status

STRATEGIES={
 "EMA_CROSS":{"fast":10,"slow":30},
 "RSI":{"period":14,"oversold":35,"overbought":65},
 "MACD":{},"MOMENTUM":{"period":15},"BOLLINGER":{"period":20,"std":2}
}

def run(root: Path, explicit_input: str=""):
    discovery=discover_historical_files(root)
    selected=Path(explicit_input) if explicit_input else (
        Path(discovery["selected"]["path"]) if discovery["selected"] else None)
    validation_file=load_json(root/"release/v87_09_to_v87_16/actual/walk_forward_stress_validation_result.json")
    validation=validation_file.get("validation",{})
    validation_summary={
      "overfit_risk_score":validation.get("overfit",{}).get("overfit_risk_score",0),
      "positive_window_pct":validation.get("walk_forward",{}).get("positive_window_pct",100)
    }
    if not selected or not selected.exists():
        return {"stage":"V89.32","stage_range":"V89.01-V89.32","state":"HISTORICAL_DATA_REQUIRED",
                "status":"PASS","discovery":discovery,"final_validation":status(root),
                "paper_only":True,"broker_write_enabled":False,"order_submission_enabled":False,
                "live_trading_enabled":False,"external_network_enabled":False}
    bars=load_bars(selected)
    benchmark=buy_hold(bars)
    results=[run_strategy(bars,name,cfg) for name,cfg in STRATEGIES.items()]
    ranked=[]
    for item in results:
        gate=evaluate(item,validation_summary,benchmark["total_return_pct"])
        ranked.append({**item,"gate":gate,"score":round(
            item["total_return_pct"]-0.5*item["maximum_drawdown_pct"]+2*item["sharpe_ratio"],4)})
    ranked.sort(key=lambda x:x["score"],reverse=True)
    for i,row in enumerate(ranked,1): row["rank"]=i
    approved=[r for r in ranked if r["gate"]["approved"]]
    champion=approved[0] if approved else None
    return {
      "stage":"V89.32","stage_range":"V89.01-V89.32",
      "state":"STRATEGY_CHAMPION_CANDIDATE_READY" if champion else "STRATEGY_PERFORMANCE_REVIEW_REQUIRED",
      "status":"PASS","historical_input":str(selected.resolve()),"bar_count":len(bars),
      "benchmark":benchmark,"strategy_rankings":ranked,"champion":champion,
      "final_validation":status(root),"discovery":discovery,
      "paper_only":True,"broker_write_enabled":False,"order_submission_enabled":False,
      "live_trading_enabled":False,"external_network_enabled":False,
      "next_phase":"V89_33_PORTFOLIO_OPTIMIZATION"
    }
