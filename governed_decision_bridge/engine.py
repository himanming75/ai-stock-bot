from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .arbitration import arbitrate
from .constraints import evaluate
from .context import build_context
from .integrity import canonical_hash


def build_decision(payload: dict[str, Any]) -> dict[str, Any]:
    context = build_context(payload)

    signal = context["signal"]
    fallback_action = str(signal.get("action", "HOLD")).upper()
    fallback_confidence = float(signal.get("confidence", 0.0))
    if fallback_confidence > 1.0:
        fallback_confidence /= 100.0

    arbitration = arbitrate(
        context["strategy_votes"],
        fallback_action=fallback_action,
        fallback_confidence=fallback_confidence,
    )

    risk = context["risk"]
    quantity = float(risk.get("recommended_quantity", 0.0))
    constraints = evaluate(context, arbitration["action"], quantity)

    candidate = {
        "symbol": context["symbol"],
        "side": arbitration["action"],
        "quantity": round(quantity, 6),
        "confidence": arbitration["confidence"],
        "decision_allowed": constraints["decision_allowed"],
        "submission_allowed": False,
        "order_type": "market",
        "time_in_force": "day",
        "blocking_reasons": constraints["blocking_reasons"],
    }

    core = {
        "context_summary": {
            "symbol": context["symbol"],
            "governance_state": context["governance"].get("state"),
            "governance_health": context["governance"].get("health"),
            "account_status": context["account"].get("status"),
            "position_count": len(context["positions"]),
            "open_order_count": len(context["open_orders"]),
            "signal_action": fallback_action,
            "signal_confidence": round(fallback_confidence, 6),
            "risk_quantity": round(quantity, 6),
        },
        "arbitration": arbitration,
        "constraints": constraints,
        "paper_order_candidate": candidate,
    }
    decision_hash = canonical_hash(core)

    return {
        "stage": "V350.64",
        "state": (
            "GOVERNED_DECISION_CANDIDATE_READY"
            if constraints["decision_allowed"]
            else "GOVERNED_DECISION_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        **core,
        "decision_hash": decision_hash,
        "integrity_algorithm": "SHA256_CANONICAL_JSON",
        "replayable": True,
        "governance_enforced": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V351_01_TO_V360_64_PAPER_ORDER_PROPOSAL_AND_APPROVAL_GATE",
    }
