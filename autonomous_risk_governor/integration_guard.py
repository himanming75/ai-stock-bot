from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .integration import evaluate_integration


def run_guard(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evaluation = evaluate_integration(results)

    policy_result = results.get("policy", {})
    policy_hash = policy_result.get("policy_hash")

    return {
        "stage": "V391.10A",
        "state": evaluation["state"],
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "policy_hash": policy_hash,
        "results": results,
        "evaluation": evaluation,
        "risk_governor_decision": evaluation["decision"],
        "risk_operations_allowed": evaluation["risk_operations_allowed"],
        "execution_authorization_allowed": False,
        "automatic_resume_enabled": False,
        "manual_review_required": evaluation["manual_review_required"],
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_01A_EXECUTION_AUTHORIZATION_FOUNDATION",
    }
