from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autonomous_decision.io import load_json, write_json, append_jsonl, digest
from autonomous_decision.signals import collect_signals
from autonomous_decision.conflicts import detect_conflicts
from autonomous_decision.veto import evaluate_vetoes
from autonomous_decision.confidence import calculate_confidence
from autonomous_decision.decision import make_decision
from autonomous_decision.approval import build_approval_gate

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v102_33_to_v102_64/input/"
        "autonomous_decision_policy.json"
    )
    orchestrator = load_json(
        root / "release/v102_01_to_v102_32/actual/"
        "master_ai_orchestrator_result.json"
    )
    regime = load_json(
        root / "release/v93_33_to_v93_64/actual/"
        "multi_timeframe_regime_result.json"
    )
    meta = load_json(
        root / "release/v94_01_to_v94_32/actual/meta_strategy_result.json"
    )
    risk = load_json(
        root / "release/v100_01_to_v100_32/actual/"
        "ai_risk_manager_result.json"
    )
    risk_budget = load_json(
        root / "release/v100_33_to_v100_64/actual/"
        "risk_budget_allocation_result.json"
    )
    adaptive = load_json(
        root / "release/v101_33_to_v101_64/actual/"
        "adaptive_rebalance_optimization_result.json"
    )

    signals = collect_signals(
        orchestrator, regime, meta, risk, risk_budget, adaptive
    )
    conflicts = detect_conflicts(signals)
    vetoes = evaluate_vetoes(signals, conflicts, policy)
    confidence = calculate_confidence(signals, conflicts, vetoes)
    decision = make_decision(
        signals, conflicts, vetoes, confidence, policy
    )
    approval = build_approval_gate(decision, confidence, policy)

    observed_at = datetime.now(timezone.utc).isoformat()
    decision_id = digest({
        "orchestration_id": orchestrator.get("orchestration_id"),
        "signals": signals,
        "policy": policy,
    })[:24]

    if decision["decision"] == "ACT":
        state = "AUTONOMOUS_DECISION_READY_FOR_MANUAL_APPROVAL"
    elif decision["decision"] == "HOLD":
        state = "AUTONOMOUS_DECISION_HOLD"
    elif decision["decision"] == "REVIEW":
        state = "AUTONOMOUS_DECISION_REVIEW_REQUIRED"
    else:
        state = "AUTONOMOUS_DECISION_BLOCKED"

    body = {
        "stage": "V102.64",
        "stage_range": "V102.33-V102.64",
        "state": state,
        "status": "PASS",
        "observed_at": observed_at,
        "decision_id": decision_id,
        "source_orchestration_id": orchestrator.get("orchestration_id"),
        "signals": signals,
        "conflict_analysis": conflicts,
        "safety_veto": vetoes,
        "confidence": confidence,
        "autonomous_decision": decision,
        "approval_gate": approval,
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
        "next_phase": "V103_01_AUTONOMOUS_CYCLE_MANAGER",
    }
    body["autonomous_decision_certificate_sha256"] = digest(body)

    write_json(
        root / "release/v102_33_to_v102_64/actual/"
        "autonomous_decision_result.json",
        body,
    )
    append_jsonl(
        root / "release/v102_33_to_v102_64/actual/"
        "autonomous_decision_ledger.jsonl",
        {
            "observed_at": observed_at,
            "decision_id": decision_id,
            "state": state,
            "decision": decision["decision"],
            "reason": decision["reason"],
            "confidence_score": confidence["confidence_score"],
            "conflict_count": conflicts["conflict_count"],
            "veto_count": vetoes["veto_count"],
            "approval_eligible": approval["approval_eligible"],
            "execution_authorized": False,
            "actual_orders_submitted": 0,
        },
    )
    return body
