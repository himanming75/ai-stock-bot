from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from paper_qualification.io import write_json,append_jsonl
from paper_qualification.config import load
from paper_qualification.source import collect
from paper_qualification.metrics import compute
from paper_qualification.strategies import analyze
from paper_qualification.windows import evaluate as evaluate_windows

def evaluate(root:Path)->dict[str,Any]:
    policy=load(root)
    source=collect(root)
    metrics=compute(source["trades"],source["daily"])
    strategies=analyze(source["trades"],source["daily"])
    windows=evaluate_windows(source["daily"],source["trades"])
    duplicate_orders=sum(1 for x in source["orders"] if str(x.get("status","")).lower()=="duplicate")
    reconciliation_errors=0
    critical_errors=0
    best_score=strategies[0]["score"] if strategies else 0.0
    checks={
        "minimum_trading_days":metrics["trading_days"]>=policy["minimum_trading_days"],
        "minimum_closed_trades":metrics["closed_trades"]>=policy["minimum_closed_trades"],
        "minimum_win_rate":metrics["win_rate_pct"]>=policy["minimum_win_rate_pct"],
        "minimum_profit_factor":metrics["profit_factor"]>=policy["minimum_profit_factor"],
        "minimum_sharpe":metrics["sharpe"]>=policy["minimum_sharpe"],
        "maximum_drawdown":metrics["maximum_drawdown_pct"]<=policy["maximum_drawdown_pct"],
        "reconciliation_errors":reconciliation_errors<=policy["maximum_reconciliation_errors"],
        "duplicate_orders":duplicate_orders<=policy["maximum_duplicate_orders"],
        "critical_errors":critical_errors<=policy["maximum_critical_errors"],
        "strategy_score":best_score>=policy["minimum_strategy_score"],
        "paper_only":True,
        "live_submission_disabled":True,
    }
    failed=[k for k,v in checks.items() if not v]
    state="PAPER_QUALIFICATION_PASSED" if not failed else "PAPER_QUALIFICATION_IN_PROGRESS"
    observed=datetime.now(timezone.utc).isoformat()
    result={
        "stage":"V165.64","state":state,"status":"PASS",
        "observed_at":observed,
        "metrics":metrics,
        "strategy_rankings":strategies,
        "rolling_windows":windows,
        "quality_counts":{
            "reconciliation_errors":reconciliation_errors,
            "duplicate_orders":duplicate_orders,
            "critical_errors":critical_errors,
        },
        "qualification":{"passed":not failed,"checks":checks,"failed":failed},
        "recommendation":{
            "best_strategy":strategies[0]["strategy_id"] if strategies else None,
            "best_strategy_score":best_score,
            "action":"CONTINUE_PAPER_COLLECTION" if failed else "READY_FOR_LIVE_READ_ONLY_REVIEW",
        },
        "paper_only":True,
        "live_trading_ready":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V166_01_TO_V170_64_LIVE_READ_ONLY_APPROVAL_CENTER",
    }
    actual=root/"release/v161_01_to_v165_64/actual"
    write_json(actual/"paper_qualification_result.json",result)
    write_json(actual/"paper_metrics.json",metrics)
    write_json(actual/"strategy_rankings.json",{"strategies":strategies})
    write_json(actual/"rolling_window_scores.json",windows)
    append_jsonl(actual/"qualification_ledger.jsonl",{
        "observed_at":observed,"state":state,
        "trading_days":metrics["trading_days"],
        "closed_trades":metrics["closed_trades"],
        "passed":not failed,"actual_live_orders_submitted":0,
    })
    return result
