from __future__ import annotations
from pathlib import Path
from typing import Any

from meta_strategy_engine.io import load_json, digest_payload
from meta_strategy_engine.scoring import strategy_meta_score
from meta_strategy_engine.allocation import allocate
from meta_strategy_engine.decision import final_position_multiplier, paper_decision

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v94_01_to_v94_32/input/meta_strategy_policy.json"
    )
    lab = load_json(
        root / "release/v91_01_to_v91_32/actual/ultimate_strategy_lab_result.json"
    )
    optimization = load_json(
        root / "release/v91_33_to_v91_64/actual/parameter_optimization_result.json"
    )
    risk = load_json(
        root / "release/v92_33_to_v92_64/actual/enterprise_risk_center_result.json"
    )
    mtf = load_json(
        root / "release/v93_33_to_v93_64/actual/multi_timeframe_regime_result.json"
    )
    explain = load_json(
        root / "release/v92_01_to_v92_32/actual/ai_explainability_pro_result.json"
    )

    source_rows = optimization.get("top_results", []) or lab.get("rankings", [])
    if not source_rows:
        return {
            "stage": "V94.32",
            "stage_range": "V94.01-V94.32",
            "state": "META_STRATEGY_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    stable_candidate = optimization.get("best_stable_candidate") or {}
    stable_strategy_id = stable_candidate.get("strategy_id")
    regime_recommendations = mtf.get("recommended_strategies", [])
    risk_approved = risk.get("risk_approved") is True
    score_weights = policy.get("score_weights", {})

    ranked = []
    for row in source_rows:
        item = dict(row)
        if "base_strategy" not in item:
            item["base_strategy"] = row.get("strategy") or row.get("strategy_name")
        scored = strategy_meta_score(
            item,
            regime_recommendations,
            stable_strategy_id,
            risk_approved,
            score_weights,
        )
        item.update(scored)
        ranked.append(item)

    ranked.sort(key=lambda item: item["meta_score"], reverse=True)
    for index, item in enumerate(ranked, 1):
        item["meta_rank"] = index

    allocations = allocate(
        ranked,
        int(policy.get("top_strategy_count", 3)),
        float(policy.get("maximum_strategy_weight_pct", 45.0)),
    )

    consensus = mtf.get("consensus", {})
    base_multiplier = float(mtf.get("effective_position_multiplier", 0.0))
    confidence = float(explain.get("confidence", {}).get("score", 50.0))
    conflict = bool(consensus.get("conflict_detected", False))
    final_multiplier = final_position_multiplier(
        base_multiplier,
        risk_approved,
        confidence,
        conflict,
    )

    checks = {
        "strategy_sources_available": bool(ranked),
        "risk_center_approved": risk_approved,
        "multi_timeframe_ready": mtf.get("state") == "MULTI_TIMEFRAME_REGIME_READY",
        "allocation_sum_valid": (
            abs(sum(float(row["weight_pct"]) for row in allocations) - 100.0) <= 0.01
            if allocations else False
        ),
        "position_multiplier_positive": final_multiplier > 0.0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    decision = paper_decision(
        allocations,
        final_multiplier,
        risk_approved,
        not failed,
    )
    state = (
        "META_STRATEGY_ENGINE_READY"
        if decision not in {"NO_ACTION", "REVIEW_REQUIRED"}
        else "META_STRATEGY_ENGINE_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V94.32",
        "stage_range": "V94.01-V94.32",
        "state": state,
        "status": "PASS",
        "paper_decision": decision,
        "selected_strategy": allocations[0] if allocations else None,
        "strategy_allocations": allocations,
        "strategy_rankings": ranked[:25],
        "stable_strategy_id": stable_strategy_id,
        "regime_recommendations": regime_recommendations,
        "market_consensus": consensus,
        "risk_approved": risk_approved,
        "explainability_confidence_score": confidence,
        "base_position_multiplier": base_multiplier,
        "final_position_multiplier": final_multiplier,
        "checks": checks,
        "failed_checks": failed,
        "policy": policy,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V94_33_DECISION_ORCHESTRATION",
    }
    body["meta_strategy_certificate_sha256"] = digest_payload(body)
    return body
