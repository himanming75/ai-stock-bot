from __future__ import annotations
from pathlib import Path
from typing import Any

from ai_explainability_pro.io import load_json, digest_payload
from ai_explainability_pro.features import extract_candidate, derive_features
from ai_explainability_pro.reasons import selection_reasons, risk_factors
from ai_explainability_pro.confidence import confidence_score
from ai_explainability_pro.narrative import strategy_description, build_summary

def explain(root: Path) -> dict[str, Any]:
    optimization = load_json(
        root / "release/v91_33_to_v91_64/actual/"
        "parameter_optimization_result.json"
    )
    candidate = extract_candidate(optimization)

    if not candidate:
        return {
            "stage": "V92.32",
            "stage_range": "V92.01-V92.32",
            "state": "AI_EXPLAINABILITY_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    features = derive_features(candidate)
    reasons = selection_reasons(features)
    risks = risk_factors(features)
    confidence = confidence_score(features, risks)
    summary = build_summary(features, reasons, risks, confidence)
    description = strategy_description(
        str(features.get("strategy_id", "")),
        features.get("parameters", {}),
    )

    body = {
        "stage": "V92.32",
        "stage_range": "V92.01-V92.32",
        "state": "AI_EXPLAINABILITY_PRO_READY",
        "status": "PASS",
        "strategy_id": features.get("strategy_id"),
        "parameters": features.get("parameters"),
        "strategy_description": description,
        "summary": summary,
        "confidence": confidence,
        "selection_reasons": reasons,
        "risk_factors": risks,
        "feature_snapshot": features,
        "decision": (
            "STABLE_CANDIDATE"
            if features.get("stability_passed")
            else "REVIEW_REQUIRED"
        ),
        "explanation_method": "deterministic_local_rule_engine",
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V92_33_ENTERPRISE_RISK_CENTER",
    }
    body["explanation_sha256"] = digest_payload(body)
    return body
