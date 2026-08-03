from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from ai_portfolio_manager.io import load_json,write_json,append_jsonl,digest
from ai_portfolio_manager.candidates import build_candidates
from ai_portfolio_manager.scoring import rank_candidates
from ai_portfolio_manager.allocation import allocate
from ai_portfolio_manager.risk import evaluate_risk

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v99_01_to_v99_32/input/portfolio_manager_policy.json"
    )
    source=load_json(
        root/"release/v98_33_to_v98_64/actual/backtest_batch_result.json"
    )

    if source.get("state")!="BACKTEST_BATCH_REGRESSION_READY":
        return {
            "stage":"V99.32",
            "stage_range":"V99.01-V99.32",
            "state":"AI_PORTFOLIO_MANAGER_SOURCE_REQUIRED",
            "status":"PASS",
            "paper_only":True,
            "broker_write_enabled":False,
            "order_submission_enabled":False,
            "live_trading_enabled":False,
            "external_network_enabled":False,
        }

    candidates=build_candidates(source.get("results",[]))
    rankings=rank_candidates(candidates,policy)
    allocation=allocate(rankings,policy)
    risk=evaluate_risk(allocation,rankings,policy)

    champion=(rankings[0] if rankings else None)
    state=(
        "AI_PORTFOLIO_MANAGER_READY"
        if risk["passed"]
        else "AI_PORTFOLIO_MANAGER_REVIEW_REQUIRED"
    )
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V99.32",
        "stage_range":"V99.01-V99.32",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "portfolio_id":digest({
            "source_batch_id":source.get("batch_id"),
            "policy":policy,
            "rankings":rankings,
        })[:24],
        "source_batch_id":source.get("batch_id"),
        "candidate_count":len(candidates),
        "rankings":rankings,
        "champion":champion,
        "allocation":allocation,
        "risk":risk,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "actual_orders_submitted":0,
        "network_requests_executed":0,
        "write_requests_executed":0,
        "paper_only":True,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "continuous_loop_enabled":False,
        "windows_task_enabled":False,
        "next_phase":"V99_33_PORTFOLIO_REBALANCE_ENGINE",
    }
    body["ai_portfolio_certificate_sha256"]=digest(body)
    write_json(
        root/"release/v99_01_to_v99_32/actual/ai_portfolio_manager_result.json",
        body,
    )
    append_jsonl(
        root/"release/v99_01_to_v99_32/actual/ai_portfolio_manager_ledger.jsonl",
        {
            "observed_at":observed,
            "portfolio_id":body["portfolio_id"],
            "state":state,
            "candidate_count":len(candidates),
            "allocated_strategy_count":allocation["allocated_strategy_count"],
            "cash_weight_pct":allocation["cash_weight_pct"],
            "risk_passed":risk["passed"],
            "champion_strategy":champion.get("strategy_id") if champion else None,
        },
    )
    return body
