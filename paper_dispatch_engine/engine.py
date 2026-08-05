from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


ALLOWED_SIDES = {"BUY", "SELL"}
ALLOWED_ORDER_TYPES = {"MARKET", "LIMIT"}
ALLOWED_TIF = {"day", "gtc", "ioc", "fok"}


def canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_dispatch_context(context: dict[str, Any]) -> dict[str, Any]:
    payload = context.get("order_payload", {})
    expected_context_core = {
        "context_version": context.get("context_version"),
        "dispatch_id": context.get("dispatch_id"),
        "proposal_id": context.get("proposal_id"),
        "token_id": context.get("token_id"),
        "release_token_id": context.get("release_token_id"),
        "policy_hash": context.get("policy_hash"),
        "order_payload_hash": context.get("order_payload_hash"),
        "release_record_hash": context.get("release_record_hash"),
        "order_payload": payload,
        "target_environment": context.get("target_environment"),
        "broker_adapter": context.get("broker_adapter"),
        "dispatch_mode": context.get("dispatch_mode"),
    }

    checks = {
        "context_state_ready": (
            context.get("context_state") == "LOCAL_DISPATCH_CONTEXT_READY"
        ),
        "context_version_valid": context.get("context_version") == "V392.09A",
        "context_id_present": bool(str(context.get("context_id", "")).strip()),
        "context_hash_matches": (
            context.get("context_hash") == canonical_hash(expected_context_core)
        ),
        "dispatch_id_present": bool(str(context.get("dispatch_id", "")).strip()),
        "proposal_id_present": bool(str(context.get("proposal_id", "")).strip()),
        "policy_hash_valid": len(str(context.get("policy_hash", ""))) == 64,
        "order_payload_hash_matches": (
            context.get("order_payload_hash") == canonical_hash(payload)
        ),
        "release_record_hash_valid": (
            len(str(context.get("release_record_hash", ""))) == 64
        ),
        "paper_only": context.get("target_environment") == "PAPER",
        "broker_adapter_none": context.get("broker_adapter") == "NONE",
        "dispatch_mode_local": (
            context.get("dispatch_mode") == "LOCAL_PREPARATION_ONLY"
        ),
        "payload_proposal_matches": (
            payload.get("proposal_id") == context.get("proposal_id")
        ),
        "payload_environment_paper": (
            payload.get("target_environment") == "PAPER"
        ),
        "symbol_present": bool(str(payload.get("symbol", "")).strip()),
        "side_valid": str(payload.get("side", "")).upper() in ALLOWED_SIDES,
        "order_type_valid": (
            str(payload.get("order_type", "")).upper() in ALLOWED_ORDER_TYPES
        ),
        "time_in_force_valid": payload.get("time_in_force") in ALLOWED_TIF,
        "notional_positive": (
            isinstance(payload.get("estimated_notional"), (int, float))
            and payload.get("estimated_notional") > 0
        ),
    }

    return {
        "valid": all(checks.values()),
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "payload_hash": canonical_hash(payload),
        "recomputed_context_hash": canonical_hash(expected_context_core),
    }


def run_local_paper_dispatch(
    context: dict[str, Any],
    dispatched_context_ids: set[str],
) -> dict[str, Any]:
    validation = validate_dispatch_context(context)
    context_id = str(context.get("context_id", "")).strip()
    dispatch_id = str(context.get("dispatch_id", "")).strip()
    payload = context.get("order_payload", {})

    replay_free = context_id not in dispatched_context_ids
    approved = validation["valid"] and replay_free

    local_execution_id = hashlib.sha256(
        f"{context_id}|{dispatch_id}|{validation['payload_hash']}".encode("utf-8")
    ).hexdigest()

    local_order = {
        "local_execution_id": local_execution_id,
        "dispatch_id": dispatch_id,
        "context_id": context_id,
        "proposal_id": context.get("proposal_id"),
        "symbol": payload.get("symbol"),
        "side": str(payload.get("side", "")).upper(),
        "order_type": str(payload.get("order_type", "")).upper(),
        "estimated_notional": payload.get("estimated_notional"),
        "time_in_force": payload.get("time_in_force"),
        "target_environment": "PAPER",
        "broker_adapter": "NONE",
        "submission_state": (
            "ACCEPTED_FOR_SIMULATION"
            if approved
            else "LOCAL_DISPATCH_REJECTED"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "state": (
            "LOCAL_PAPER_DISPATCH_ACCEPTED"
            if approved
            else "LOCAL_PAPER_DISPATCH_BLOCKED"
        ),
        "approved": approved,
        "context_validation": validation,
        "context_not_dispatched": replay_free,
        "replay_detected": not replay_free,
        "local_execution_id": local_execution_id,
        "local_order": local_order,
        "local_order_hash": canonical_hash(local_order),
        "failed": (
            validation["failed"]
            + ([] if replay_free else ["CONTEXT_ALREADY_DISPATCHED"])
        ),
        "required_action": (
            "ALLOW_PAPER_EXECUTION_SIMULATOR_STAGE"
            if approved
            else "DO_NOT_CREATE_SIMULATED_EXECUTION"
        ),
        "broker_network_used": False,
        "broker_submission_attempted": False,
    }
