from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_order_payload(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "symbol": proposal.get("symbol"),
        "side": proposal.get("side"),
        "order_type": proposal.get("order_type"),
        "estimated_notional": proposal.get("estimated_notional"),
        "time_in_force": proposal.get("time_in_force", "day"),
        "target_environment": "PAPER",
    }


def evaluate_dispatch_preparation(
    token_gate_result: dict[str, Any],
    proposal: dict[str, Any],
    dispatch_request: dict[str, Any],
    queued_dispatch_ids: set[str],
) -> dict[str, Any]:
    order_payload = build_order_payload(proposal)
    order_payload_hash = canonical_hash(order_payload)

    dispatch_id = str(dispatch_request.get("dispatch_id", "")).strip()
    token_id = str(token_gate_result.get("token_id", "")).strip()
    proposal_id = str(proposal.get("proposal_id", "")).strip()
    policy_hash = str(
        token_gate_result
        .get("authorization_result", {})
        .get("policy_hash", "")
    ).strip()

    checks = {
        "token_gate_stage_valid": token_gate_result.get("stage") == "V392.02A",
        "token_gate_status_pass": token_gate_result.get("status") == "PASS",
        "token_gate_open": (
            token_gate_result.get("state") == "AUTHORIZATION_TOKEN_GATE_OPEN"
        ),
        "token_gate_allowed": token_gate_result.get("token_gate_allowed") is True,
        "dispatch_preparation_allowed": (
            token_gate_result.get("dispatch_preparation_allowed") is True
        ),
        "dispatch_id_present": bool(dispatch_id),
        "dispatch_not_queued": dispatch_id not in queued_dispatch_ids,
        "token_id_present": bool(token_id),
        "token_id_matches": dispatch_request.get("token_id") == token_id,
        "proposal_id_present": bool(proposal_id),
        "proposal_id_matches": dispatch_request.get("proposal_id") == proposal_id,
        "policy_hash_present": bool(policy_hash),
        "policy_hash_matches": dispatch_request.get("policy_hash") == policy_hash,
        "order_payload_hash_matches": (
            dispatch_request.get("order_payload_hash") == order_payload_hash
        ),
        "paper_only": dispatch_request.get("target_environment") == "PAPER",
        "broker_submission_disabled": (
            dispatch_request.get("broker_submission_enabled") is False
        ),
        "automatic_dispatch_disabled": (
            dispatch_request.get("automatic_dispatch") is not True
        ),
    }

    approved = all(checks.values())

    return {
        "state": (
            "DISPATCH_PREPARATION_ACCEPTED"
            if approved
            else "DISPATCH_PREPARATION_REJECTED"
        ),
        "approved": approved,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "dispatch_id": dispatch_id,
        "token_id": token_id,
        "proposal_id": proposal_id,
        "policy_hash": policy_hash,
        "order_payload": order_payload,
        "order_payload_hash": order_payload_hash,
        "replay_detected": not checks["dispatch_not_queued"],
        "required_action": (
            "CREATE_LOCAL_DISPATCH_QUEUE_ENTRY"
            if approved
            else "DO_NOT_CREATE_DISPATCH_QUEUE_ENTRY"
        ),
    }
