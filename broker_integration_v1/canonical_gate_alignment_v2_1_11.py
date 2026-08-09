from __future__ import annotations

from decimal import Decimal

from ai_engine_v2.promotion_gate_v3_21 import MIN_COMPARISONS
from ai_engine_v2.safety_supervisor_v3_29 import build_safety_supervisor
from .etrade_ai_signal_decision_v2_1_5 import SignalDecisionPolicy


CANONICAL_SIGNAL_MIN_CONFIDENCE=Decimal("0.60")
CANONICAL_PROMOTION_MIN_COMPARISONS=20


def build_canonical_gate_alignment_v2_1_11():
    signal_policy=SignalDecisionPolicy().validate()
    safety=build_safety_supervisor()
    locks=safety.get("locks") or {}

    checks={
        "signal_min_confidence_matches":
            signal_policy.minimum_confidence
            == CANONICAL_SIGNAL_MIN_CONFIDENCE,
        "promotion_min_comparisons_matches":
            int(MIN_COMPARISONS)
            == CANONICAL_PROMOTION_MIN_COMPARISONS,
        "live_trading_locked":
            locks.get("live_trading_locked") is True,
        "broker_write_locked":
            locks.get("broker_write_locked") is True,
        "automatic_promotion_locked":
            locks.get("automatic_promotion_locked") is True,
        "automatic_strategy_change_locked":
            locks.get("automatic_strategy_change_locked") is True,
    }

    aligned=all(checks.values())

    return {
        "stage":"BROKER_INTEGRATION_V2_1_11_CANONICAL_GATE_ALIGNMENT",
        "status":"PASS_CANONICAL_GATE_ALIGNMENT" if aligned else "BLOCK_CANONICAL_GATE_MISMATCH",
        "aligned":aligned,
        "signal_gate":{
            "minimum_confidence":str(signal_policy.minimum_confidence),
            "allowed_actions":list(signal_policy.allowed_actions),
        },
        "promotion_gate":{
            "minimum_comparisons":int(MIN_COMPARISONS),
            "automatic_promotion":False,
            "manual_review_required":True,
        },
        "safety_locks":locks,
        "checks":checks,
        "sandbox_execution_allowed_when_signal_eligible":aligned,
        "production_order_post_allowed":False,
        "live_trading_enabled":False,
        "profitability_validation":False,
    }


def require_canonical_gate_alignment_v2_1_11():
    result=build_canonical_gate_alignment_v2_1_11()
    if not result["aligned"]:
        failed=[
            key for key,value in result["checks"].items()
            if not value
        ]
        raise RuntimeError(
            "Canonical gate alignment failed: "
            +", ".join(failed)
        )
    return result
