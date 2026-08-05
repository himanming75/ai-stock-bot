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


def build_dispatch_context(
    release_gate_result: dict[str, Any],
    preparation_result: dict[str, Any],
    existing_context_ids: set[str],
) -> dict[str, Any]:
    release_eval = release_gate_result.get("evaluation", {})
    release_record = release_eval.get("release_record", {})
    preparation_eval = preparation_result.get("evaluation", {})
    order_payload = preparation_eval.get("order_payload", {})

    dispatch_id = str(release_record.get("dispatch_id", "")).strip()
    proposal_id = str(release_record.get("proposal_id", "")).strip()
    token_id = str(release_record.get("token_id", "")).strip()
    policy_hash = str(release_record.get("policy_hash", "")).strip()
    order_payload_hash = str(release_record.get("order_payload_hash", "")).strip()
    release_record_hash = str(release_eval.get("release_record_hash", "")).strip()

    context_core = {
        "context_version": "V392.09A",
        "dispatch_id": dispatch_id,
        "proposal_id": proposal_id,
        "token_id": token_id,
        "release_token_id": release_record.get("release_token_id"),
        "policy_hash": policy_hash,
        "order_payload_hash": order_payload_hash,
        "release_record_hash": release_record_hash,
        "order_payload": order_payload,
        "target_environment": "PAPER",
        "broker_adapter": "NONE",
        "dispatch_mode": "LOCAL_PREPARATION_ONLY",
    }
    context_hash = canonical_hash(context_core)
    context_id = hashlib.sha256(
        f"{dispatch_id}|{proposal_id}|{context_hash}".encode("utf-8")
    ).hexdigest()

    checks = {
        "release_gate_stage_valid": release_gate_result.get("stage") == "V392.08A",
        "release_gate_status_pass": release_gate_result.get("status") == "PASS",
        "release_gate_ready": (
            release_gate_result.get("state") == "LOCAL_DISPATCH_RELEASE_GATE_READY"
        ),
        "release_approved": (
            release_gate_result.get("local_dispatch_release_approved") is True
        ),
        "engine_preparation_allowed": (
            release_gate_result.get(
                "local_dispatch_engine_preparation_allowed"
            ) is True
        ),
        "preparation_stage_valid": preparation_result.get("stage") == "V392.03A",
        "preparation_status_pass": preparation_result.get("status") == "PASS",
        "dispatch_id_matches": (
            dispatch_id == preparation_eval.get("dispatch_id")
        ),
        "proposal_id_matches": (
            proposal_id == preparation_eval.get("proposal_id")
        ),
        "token_id_matches": token_id == preparation_eval.get("token_id"),
        "policy_hash_matches": (
            policy_hash == preparation_eval.get("policy_hash")
        ),
        "order_payload_hash_matches": (
            order_payload_hash == preparation_eval.get("order_payload_hash")
            == canonical_hash(order_payload)
        ),
        "release_record_hash_present": len(release_record_hash) == 64,
        "context_not_created": context_id not in existing_context_ids,
        "paper_only": release_record.get("target_environment") == "PAPER",
        "broker_adapter_none": context_core["broker_adapter"] == "NONE",
    }

    approved = all(checks.values())

    context = {
        **context_core,
        "context_id": context_id,
        "context_hash": context_hash,
        "context_state": (
            "LOCAL_DISPATCH_CONTEXT_READY"
            if approved
            else "LOCAL_DISPATCH_CONTEXT_BLOCKED"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "state": (
            "LOCAL_DISPATCH_CONTEXT_ACCEPTED"
            if approved
            else "LOCAL_DISPATCH_CONTEXT_REJECTED"
        ),
        "approved": approved,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "dispatch_context": context,
        "context_id": context_id,
        "context_hash": context_hash,
        "replay_detected": not checks["context_not_created"],
        "required_action": (
            "ALLOW_LOCAL_PAPER_DISPATCH_ENGINE_STAGE"
            if approved
            else "DO_NOT_START_LOCAL_DISPATCH_ENGINE"
        ),
    }
