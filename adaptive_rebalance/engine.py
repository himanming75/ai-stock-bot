from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adaptive_rebalance.io import load_json, write_json, append_jsonl, digest
from adaptive_rebalance.regime import normalize_regime, regime_multiplier
from adaptive_rebalance.optimizer import optimize_adjustments
from adaptive_rebalance.stability import stability_score
from adaptive_rebalance.gate import evaluate_gate

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v101_33_to_v101_64/input/adaptive_rebalance_policy.json"
    )
    control = load_json(
        root / "release/v101_01_to_v101_32/actual/"
        "portfolio_rebalance_control_result.json"
    )
    regime_source = load_json(
        root / "release/v93_33_to_v93_64/actual/"
        "multi_timeframe_regime_result.json"
    )
    risk_budget = load_json(
        root / "release/v100_33_to_v100_64/actual/"
        "risk_budget_allocation_result.json"
    )

    if (
        control.get("state") != "PORTFOLIO_REBALANCE_CONTROL_READY"
        or risk_budget.get("state") != "RISK_BUDGET_ALLOCATION_READY"
    ):
        return {
            "stage": "V101.64",
            "stage_range": "V101.33-V101.64",
            "state": "ADAPTIVE_REBALANCE_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    regime = normalize_regime(regime_source)
    multiplier = regime_multiplier(regime, policy)
    optimized = optimize_adjustments(control, multiplier, policy)
    stability = stability_score(optimized, control, policy)
    gate = evaluate_gate(optimized, stability, policy)

    actionable = [row for row in optimized if row.get("state") == "OPTIMIZED"]
    state = (
        "ADAPTIVE_REBALANCE_OPTIMIZATION_READY"
        if gate["passed"] and actionable
        else (
            "ADAPTIVE_REBALANCE_OPTIMIZATION_NO_ACTION"
            if gate["passed"]
            else "ADAPTIVE_REBALANCE_OPTIMIZATION_REVIEW_REQUIRED"
        )
    )

    observed = datetime.now(timezone.utc).isoformat()
    body = {
        "stage": "V101.64",
        "stage_range": "V101.33-V101.64",
        "state": state,
        "status": "PASS",
        "observed_at": observed,
        "adaptive_rebalance_id": digest({
            "control_id": control.get("rebalance_control_id"),
            "risk_budget_id": risk_budget.get("risk_budget_id"),
            "regime": regime,
            "policy": policy,
        })[:24],
        "source_rebalance_control_id": control.get("rebalance_control_id"),
        "source_risk_budget_id": risk_budget.get("risk_budget_id"),
        "regime": regime,
        "regime_multiplier": multiplier,
        "optimized_adjustments": optimized,
        "actionable_adjustment_count": len(actionable),
        "stability": stability,
        "optimization_gate": gate,
        "execution_authorized": False,
        "manual_approval_required": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "next_phase": "V102_01_MASTER_AI_ORCHESTRATOR",
    }
    body["adaptive_rebalance_certificate_sha256"] = digest(body)

    write_json(
        root / "release/v101_33_to_v101_64/actual/"
        "adaptive_rebalance_optimization_result.json",
        body,
    )
    append_jsonl(
        root / "release/v101_33_to_v101_64/actual/"
        "adaptive_rebalance_optimization_ledger.jsonl",
        {
            "observed_at": observed,
            "adaptive_rebalance_id": body["adaptive_rebalance_id"],
            "state": state,
            "regime": regime["primary_regime"],
            "volatility_regime": regime["volatility_regime"],
            "actionable_adjustment_count": len(actionable),
            "stability_score": stability["stability_score"],
            "gate_passed": gate["passed"],
        },
    )
    return body
