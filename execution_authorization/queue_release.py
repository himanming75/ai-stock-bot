from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


REQUIRED_APPROVAL_PHRASE = "APPROVE_FIFO_QUEUE_RELEASE"


def canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("RELEASE_TIMESTAMP_REQUIRED")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evaluate_queue_release(
    inspection_result: dict[str, Any],
    queue_state: dict[str, Any],
    release_request: dict[str, Any],
    consumed_release_ids: set[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    evaluation = inspection_result.get("evaluation", {})
    head = evaluation.get("head_entry") or {}
    entries = queue_state.get("entries", [])
    queue_head = entries[0] if entries else {}

    release_id = str(release_request.get("release_id", "")).strip()
    expires_at = parse_utc(release_request.get("expires_at"))

    current_queue_hash = canonical_hash(queue_state)
    current_head_hash = canonical_hash(queue_head) if queue_head else ""

    checks = {
        "inspection_stage_valid": inspection_result.get("stage") == "V392.05A",
        "inspection_status_pass": inspection_result.get("status") == "PASS",
        "inspection_gate_ready": (
            inspection_result.get("state") == "QUEUE_INSPECTION_GATE_READY"
        ),
        "inspection_passed": (
            inspection_result.get("queue_release_inspection_passed") is True
        ),
        "release_authorization_allowed": (
            inspection_result.get("release_authorization_allowed") is True
        ),
        "queue_present": bool(entries),
        "queue_unlocked": queue_state.get("lock", {}).get("locked") is not True,
        "head_status_queued": queue_head.get("status") == "QUEUED",
        "head_sequence_one": queue_head.get("sequence") == 1,
        "dispatch_id_matches": (
            release_request.get("dispatch_id")
            == head.get("dispatch_id")
            == queue_head.get("dispatch_id")
        ),
        "token_id_matches": (
            release_request.get("token_id") == queue_head.get("token_id")
        ),
        "proposal_id_matches": (
            release_request.get("proposal_id") == queue_head.get("proposal_id")
        ),
        "queue_hash_matches": (
            release_request.get("queue_hash")
            == evaluation.get("queue_hash")
            == current_queue_hash
        ),
        "head_entry_hash_matches": (
            release_request.get("head_entry_hash")
            == head.get("entry_hash")
            == current_head_hash
        ),
        "release_id_present": bool(release_id),
        "release_not_consumed": release_id not in consumed_release_ids,
        "approval_phrase_valid": (
            release_request.get("approval_phrase") == REQUIRED_APPROVAL_PHRASE
        ),
        "approved_by_present": bool(
            str(release_request.get("approved_by", "")).strip()
        ),
        "reason_present": bool(str(release_request.get("reason", "")).strip()),
        "not_expired": current_time <= expires_at,
        "paper_only": release_request.get("target_environment") == "PAPER",
        "automatic_release_disabled": (
            release_request.get("automatic_release") is not True
        ),
        "dispatch_execution_disabled": (
            release_request.get("dispatch_execution_enabled") is False
        ),
    }

    approved = all(checks.values())

    return {
        "state": (
            "QUEUE_RELEASE_AUTHORIZATION_APPROVED"
            if approved
            else "QUEUE_RELEASE_AUTHORIZATION_BLOCKED"
        ),
        "approved": approved,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "release_id": release_id,
        "dispatch_id": queue_head.get("dispatch_id"),
        "token_id": queue_head.get("token_id"),
        "proposal_id": queue_head.get("proposal_id"),
        "queue_hash": current_queue_hash,
        "head_entry_hash": current_head_hash,
        "expires_at": expires_at.isoformat(),
        "replay_detected": not checks["release_not_consumed"],
        "required_action": (
            "ALLOW_LOCAL_RELEASE_TOKEN_STAGE"
            if approved
            else "KEEP_QUEUE_ENTRY_QUEUED"
        ),
        "queue_mutation_allowed": False,
        "dispatch_execution_allowed": False,
    }
