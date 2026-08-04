from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from risk_budget.io import load_json,write_json,append_jsonl,digest
from risk_budget.candidates import build_candidates
from risk_budget.allocation import allocate_risk_budgets
from risk_budget.exposure import dynamic_exposure_control
from risk_budget.heat import portfolio_heat
from risk_budget.gate import evaluate_gate

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v100_33_to_v100_64/input/risk_budget_policy.json"
    )
    metrics=load_json(
        root/"release/v100_33_to_v100_64/input/strategy_risk_metrics.json"
    )
    portfolio=load_json(
        root/"release/v99_01_to_v99_32/actual/"
        "ai_portfolio_manager_result.json"
    )
    risk=load_json(
        root/"release/v100_01_to_v100_32/actual/"
        "ai_risk_manager_result.json"
    )

    if (
        portfolio.get("state")!="AI_PORTFOLIO_MANAGER_READY"
        or risk.get("state")!="AI_RISK_MANAGER_READY"
    ):
        return {
            "stage":"V100.64",
            "stage_range":"V100.33-V100.64",
            "state":"RISK_BUDGET_SOURCE_REQUIRED",
            "status":"PASS",
            "paper_only":True,
            "broker_write_enabled":False,
            "order_submission_enabled":False,
            "live_trading_enabled":False,
            "external_network_enabled":False,
        }

    candidates=build_candidates(portfolio,metrics)
    allocation=allocate_risk_budgets(candidates,risk,policy)
    exposure=dynamic_exposure_control(allocation,portfolio,risk,policy)
    heat=portfolio_heat(allocation.get("allocations",[]),exposure)
    gate=evaluate_gate(allocation,exposure,heat,policy)

    state=(
        "RISK_BUDGET_ALLOCATION_READY"
        if gate["passed"]
        else "RISK_BUDGET_ALLOCATION_REVIEW_REQUIRED"
    )
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V100.64",
        "stage_range":"V100.33-V100.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "risk_budget_id":digest({
            "portfolio_id":portfolio.get("portfolio_id"),
            "risk_assessment_id":risk.get("risk_assessment_id"),
            "policy":policy,
            "metrics":metrics,
        })[:24],
        "source_portfolio_id":portfolio.get("portfolio_id"),
        "source_risk_assessment_id":risk.get("risk_assessment_id"),
        "candidate_count":len(candidates),
        "candidates":candidates,
        "risk_budget_allocation":allocation,
        "dynamic_exposure_control":exposure,
        "portfolio_heat":heat,
        "risk_budget_gate":gate,
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
        "next_phase":"V101_01_PORTFOLIO_REBALANCE_CONTROL",
    }
    body["risk_budget_certificate_sha256"]=digest(body)

    write_json(
        root/"release/v100_33_to_v100_64/actual/"
        "risk_budget_allocation_result.json",
        body,
    )
    append_jsonl(
        root/"release/v100_33_to_v100_64/actual/"
        "risk_budget_allocation_ledger.jsonl",
        {
            "observed_at":observed,
            "risk_budget_id":body["risk_budget_id"],
            "state":state,
            "candidate_count":len(candidates),
            "used_risk_budget_pct":allocation["used_risk_budget_pct"],
            "target_gross_exposure_pct":exposure["target_gross_exposure_pct"],
            "portfolio_heat_pct":heat["portfolio_heat_pct"],
            "gate_passed":gate["passed"],
        },
    )
    return body
