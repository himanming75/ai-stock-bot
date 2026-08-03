from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_risk_manager.io import load_json,write_json,append_jsonl,digest
from ai_risk_manager.exposure import calculate_exposure
from ai_risk_manager.var import portfolio_var
from ai_risk_manager.drawdown import drawdown_risk
from ai_risk_manager.stress import stress_test
from ai_risk_manager.scoring import risk_score
from ai_risk_manager.gate import evaluate_gate

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v100_01_to_v100_32/input/ai_risk_policy.json"
    )
    portfolio=load_json(
        root/"release/v99_01_to_v99_32/actual/"
        "ai_portfolio_manager_result.json"
    )
    rebalance=load_json(
        root/"release/v99_33_to_v99_64/actual/"
        "portfolio_rebalance_result.json"
    )

    if portfolio.get("state")!="AI_PORTFOLIO_MANAGER_READY":
        return {
            "stage":"V100.32","stage_range":"V100.01-V100.32",
            "state":"AI_RISK_MANAGER_SOURCE_REQUIRED","status":"PASS",
            "paper_only":True,"broker_write_enabled":False,
            "order_submission_enabled":False,"live_trading_enabled":False,
            "external_network_enabled":False,
        }

    account_equity=float(rebalance.get("account_equity",0.0))
    exposure=calculate_exposure(portfolio,rebalance)
    volatility=float(policy.get("weighted_volatility_pct",1.5))
    var_result=portfolio_var(
        account_equity,
        volatility,
        int(policy.get("var_horizon_days",1)),
    )
    drawdown=drawdown_risk(portfolio,policy)
    stress=stress_test(account_equity,exposure,policy)
    score=risk_score(exposure,var_result,drawdown,stress,policy)
    gate=evaluate_gate(
        exposure,var_result,drawdown,stress,score,rebalance,policy
    )

    state=(
        "AI_RISK_MANAGER_READY"
        if gate["passed"]
        else "AI_RISK_MANAGER_REVIEW_REQUIRED"
    )
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V100.32",
        "stage_range":"V100.01-V100.32",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "risk_assessment_id":digest({
            "portfolio_id":portfolio.get("portfolio_id"),
            "rebalance_id":rebalance.get("rebalance_id"),
            "policy":policy,
        })[:24],
        "source_portfolio_id":portfolio.get("portfolio_id"),
        "source_rebalance_id":rebalance.get("rebalance_id"),
        "account_equity":round(account_equity,6),
        "exposure":exposure,
        "value_at_risk":var_result,
        "drawdown":drawdown,
        "stress":stress,
        "risk_score":score,
        "pre_execution_gate":gate,
        "execution_authorized":False,
        "manual_approval_required":True,
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
        "next_phase":"V100_33_RISK_BUDGET_ALLOCATION",
    }
    body["ai_risk_manager_certificate_sha256"]=digest(body)
    write_json(
        root/"release/v100_01_to_v100_32/actual/"
        "ai_risk_manager_result.json",
        body,
    )
    append_jsonl(
        root/"release/v100_01_to_v100_32/actual/"
        "ai_risk_manager_ledger.jsonl",
        {
            "observed_at":observed,
            "risk_assessment_id":body["risk_assessment_id"],
            "state":state,
            "risk_score":score["risk_score"],
            "risk_level":score["risk_level"],
            "gate_passed":gate["passed"],
            "var_pct":var_result["var_pct"],
            "worst_stress_loss_pct":stress["worst_estimated_loss_pct"],
        },
    )
    return body
