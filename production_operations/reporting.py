from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_operations.io import load_json,read_jsonl,write_json

def _f(value:Any)->float:
    try:return float(value)
    except Exception:return 0.0

def collect(root:Path)->dict[str,Any]:
    qualification=load_json(root/"release/v161_01_to_v165_64/actual/paper_qualification_result.json")
    portfolio=load_json(root/"release/v181_01_to_v185_64/actual/portfolio_broker_result.json")
    paper=load_json(root/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json")
    daily=read_jsonl(root/"release/v106_33_to_v108_64/actual/daily_performance_ledger.jsonl")
    cycles=read_jsonl(root/"release/v137_01_to_v139_64/actual/autonomous_cycle_ledger.jsonl")
    return {"qualification":qualification,"portfolio":portfolio,"paper":paper,"daily":daily,"cycles":cycles}

def summarize_rows(rows:list[dict[str,Any]])->dict[str,Any]:
    returns=[_f(x.get("daily_return_pct",0)) for x in rows]
    pnl=[_f(x.get("total_pnl",x.get("realized_pnl",0))) for x in rows]
    equities=[_f(x.get("ending_equity",0)) for x in rows if _f(x.get("ending_equity",0))>0]
    return {
        "observation_count":len(rows),
        "total_pnl":round(sum(pnl),2),
        "average_daily_return_pct":round(sum(returns)/len(returns),4) if returns else 0.0,
        "positive_days":sum(1 for x in returns if x>0),
        "negative_days":sum(1 for x in returns if x<0),
        "latest_equity":equities[-1] if equities else 0.0,
        "minimum_equity":min(equities) if equities else 0.0,
        "maximum_equity":max(equities) if equities else 0.0,
    }

def build(root:Path)->dict[str,Any]:
    source=collect(root)
    daily_rows=source["daily"]
    portfolio=source["portfolio"].get("portfolio",{})
    qualification=source["qualification"]
    now=datetime.now(timezone.utc).isoformat()
    report={
        "generated_at":now,
        "daily":summarize_rows(daily_rows[-1:]),
        "weekly":summarize_rows(daily_rows[-5:]),
        "monthly":summarize_rows(daily_rows[-22:]),
        "portfolio_summary":portfolio.get("summary",{}),
        "symbol_allocation":portfolio.get("symbol_allocation",[]),
        "strategy_allocation":portfolio.get("strategy_allocation",[]),
        "broker_allocation":portfolio.get("broker_allocation",[]),
        "qualification":{
            "state":qualification.get("state","NOT_AVAILABLE"),
            "passed":qualification.get("qualification",{}).get("passed",False),
            "metrics":qualification.get("metrics",{}),
        },
        "paper_account":{
            "equity":source["paper"].get("account_equity"),
            "market_open":source["paper"].get("market_open"),
            "paper_orders_submitted":source["paper"].get("actual_paper_orders_submitted",0),
        },
        "live_orders_submitted":0,
    }
    actual=root/"release/v186_01_to_v190_64/actual"
    write_json(actual/"production_report.json",report)
    write_json(actual/"daily_report.json",report["daily"])
    write_json(actual/"weekly_report.json",report["weekly"])
    write_json(actual/"monthly_report.json",report["monthly"])
    return report
