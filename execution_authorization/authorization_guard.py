from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .policy import validate_policy
from .token import canonical_hash, parse_utc


REQUIRED_APPROVAL_PHRASE = "APPROVE_PAPER_EXECUTION_AUTHORIZATION"


def run_authorization(
    policy: dict[str, Any],
    risk_result: dict[str, Any],
    proposal: dict[str, Any],
    request: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    policy_validation = validate_policy(policy)
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    proposal_id = str(proposal.get("proposal_id", "")).strip()
    proposal_hash = canonical_hash(proposal)
    risk_policy_hash = str(risk_result.get("policy_hash", "")).strip()

    expires_at = parse_utc(request.get("expires_at"))

    checks = {
        "policy_valid": policy_validation["valid"],
        "risk_stage_valid": risk_result.get("stage") == "V391.10A",
        "risk_status_pass": risk_result.get("status") == "PASS",
        "risk_decision_allow": risk_result.get("risk_governor_decision") == "ALLOW",
        "risk_operations_allowed": risk_result.get("risk_operations_allowed") is True,
        "proposal_id_present": bool(proposal_id),
        "proposal_id_matches": request.get("proposal_id") == proposal_id,
        "proposal_hash_matches": request.get("proposal_hash") == proposal_hash,
        "policy_hash_matches": request.get("policy_hash") == risk_policy_hash,
        "approval_phrase_valid": (
            request.get("approval_phrase") == REQUIRED_APPROVAL_PHRASE
        ),
        "approved_by_present": bool(str(request.get("approved_by", "")).strip()),
        "reason_present": bool(str(request.get("reason", "")).strip()),
        "not_expired": current_time <= expires_at,
        "paper_only": request.get("target_environment") == "PAPER",
        "automatic_authorization_disabled": (
            request.get("automatic_authorization") is not True
        ),
    }

    approved = all(checks.values())

    return {
        "stage": "V392.01A",
        "state": (
            "EXECUTION_AUTHORIZATION_APPROVED"
            if approved
            else "EXECUTION_AUTHORIZATION_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": current_time.astimezone(timezone.utc).isoformat(),
        "policy_validation": policy_validation,
        "proposal_id": proposal_id,
        "proposal_hash": proposal_hash,
        "policy_hash": risk_policy_hash,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "authorization_approved": approved,
        "execution_authorization_allowed": approved,
        "required_action": (
            "ALLOW_DISPATCH_PREPARATION"
            if approved
            else "DO_NOT_PREPARE_DISPATCH"
        ),
        "automatic_authorization_enabled": False,
        "manual_approval_required": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_02A_AUTHORIZATION_TOKEN_GATE",
    }
