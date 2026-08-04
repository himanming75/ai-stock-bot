from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import secrets

from .approval import create_token
from .checks import run_checks
from .integrity import canonical_hash


def build_proposal(decision: dict[str, Any], runtime: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    checks = run_checks(decision, runtime, policy)
    candidate = decision.get("paper_order_candidate", {})

    proposal_core = {
        "symbol": str(candidate.get("symbol", "")).upper(),
        "side": str(candidate.get("side", "")).upper(),
        "quantity": round(float(candidate.get("quantity", 0.0)), 6),
        "order_type": str(candidate.get("order_type", "market")).lower(),
        "time_in_force": str(candidate.get("time_in_force", "day")).lower(),
        "reference_price": round(float(runtime.get("reference_price", 0.0)), 6),
        "estimated_notional": checks["estimated_notional"],
        "decision_hash": decision.get("decision_hash"),
        "decision_confidence": candidate.get("confidence"),
        "eligible_for_approval": checks["eligible_for_approval"],
        "blocking_reasons": checks["blocking_reasons"],
        "submission_allowed": False,
        "paper_endpoint_only": True,
    }

    proposal_hash = canonical_hash(proposal_core)
    token = create_token(
        proposal_hash=proposal_hash,
        ttl_seconds=int(policy.get("approval_token_ttl_seconds", 300)),
        nonce=secrets.token_hex(16),
    )

    state = (
        "PAPER_ORDER_PROPOSAL_AWAITING_APPROVAL"
        if checks["eligible_for_approval"]
        else "PAPER_ORDER_PROPOSAL_BLOCKED"
    )

    return {
        "stage": "V360.64",
        "state": state,
        "status": "PASS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "proposal": proposal_core,
        "proposal_hash": proposal_hash,
        "integrity_algorithm": "SHA256_CANONICAL_JSON",
        "approval": token,
        "checks": checks,
        "final_safety_audit": {
            "paper_endpoint_only": True,
            "paper_submission_enabled": False,
            "live_submission_enabled": False,
            "broker_write_enabled": False,
            "submission_allowed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
        },
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "next_phase": "V361_01_TO_V370_64_CONTROLLED_PAPER_AUTO_EXECUTION",
    }
