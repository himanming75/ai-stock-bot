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


def evaluate_local_dispatch_release(
    release_token_result: dict[str, Any],
    queue_state: dict[str, Any],
    released_dispatch_ids: set[str],
) -> dict[str, Any]:
    evaluation = release_token_result.get("evaluation", {})
    entries = queue_state.get("entries", [])
    head = entries[0] if entries else {}

    dispatch_id = str(evaluation.get("dispatch_id", "")).strip()
    release_token_id = str(evaluation.get("release_token_id", "")).strip()
    proposal_id = str(evaluation.get("proposal_id", "")).strip()
    current_queue_hash = canonical_hash(queue_state)
    current_head_hash = canonical_hash(head) if head else ""

    checks = {
        "release_token_stage_valid": release_token_result.get("stage") == "V392.07A",
        "release_token_status_pass": release_token_result.get("status") == "PASS",
        "release_token_gate_open": (
            release_token_result.get("state") == "RELEASE_TOKEN_GATE_OPEN"
        ),
        "release_token_gate_allowed": (
            release_token_result.get("release_token_gate_allowed") is True
        ),
        "local_dispatch_release_allowed": (
            release_token_result.get("local_dispatch_release_allowed") is True
        ),
        "queue_present": bool(entries),
        "queue_unlocked": queue_state.get("lock", {}).get("locked") is not True,
        "head_status_queued": head.get("status") == "QUEUED",
        "head_sequence_one": head.get("sequence") == 1,
        "dispatch_id_present": bool(dispatch_id),
        "dispatch_id_matches": dispatch_id == head.get("dispatch_id"),
        "proposal_id_present": bool(proposal_id),
        "proposal_id_matches": proposal_id == head.get("proposal_id"),
        "release_token_id_present": bool(release_token_id),
        "queue_hash_matches": (
            evaluation.get("checks", {}).get("queue_hash_matches") is True
        ),
        "head_entry_hash_matches": (
            evaluation.get("checks", {}).get("head_entry_hash_matches") is True
        ),
        "current_queue_hash_present": len(current_queue_hash) == 64,
        "current_head_hash_present": len(current_head_hash) == 64,
        "dispatch_not_released": dispatch_id not in released_dispatch_ids,
        "paper_only": head.get("target_environment") == "PAPER",
    }

    approved = all(checks.values())

    release_record = {
        "release_record_version": "V392.08A",
        "dispatch_id": dispatch_id,
        "release_token_id": release_token_id,
        "proposal_id": proposal_id,
        "token_id": head.get("token_id"),
        "policy_hash": head.get("policy_hash"),
        "order_payload_hash": head.get("order_payload_hash"),
        "queue_hash": current_queue_hash,
        "head_entry_hash": current_head_hash,
        "target_environment": "PAPER",
        "release_state": "LOCAL_RELEASE_READY" if approved else "LOCAL_RELEASE_BLOCKED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "state": (
            "LOCAL_DISPATCH_RELEASE_ACCEPTED"
            if approved
            else "LOCAL_DISPATCH_RELEASE_REJECTED"
        ),
        "approved": approved,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "release_record": release_record,
        "release_record_hash": canonical_hash(release_record),
        "replay_detected": not checks["dispatch_not_released"],
        "required_action": (
            "ALLOW_LOCAL_DISPATCH_ENGINE_PREPARATION"
            if approved
            else "KEEP_DISPATCH_QUEUED"
        ),
    }
