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


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("QUEUE_TIMESTAMP_REQUIRED")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def inspect_queue(
    queue_state: dict[str, Any],
    maximum_entry_age_seconds: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    entries = queue_state.get("entries", [])
    lock = queue_state.get("lock", {})
    errors: list[str] = []
    warnings: list[str] = []
    inspected_entries: list[dict[str, Any]] = []

    if not isinstance(entries, list):
        errors.append("ENTRIES_MUST_BE_LIST")
        entries = []

    if not isinstance(lock, dict):
        errors.append("LOCK_MUST_BE_OBJECT")
        lock = {}

    dispatch_ids: list[str] = []
    sequences: list[int] = []

    for entry in entries:
        dispatch_id = str(entry.get("dispatch_id", "")).strip()
        sequence = entry.get("sequence")
        status = str(entry.get("status", "")).strip()
        target = str(entry.get("target_environment", "")).strip()
        token_id = str(entry.get("token_id", "")).strip()
        proposal_id = str(entry.get("proposal_id", "")).strip()
        payload_hash = str(entry.get("order_payload_hash", "")).strip()
        policy_hash = str(entry.get("policy_hash", "")).strip()

        entry_errors: list[str] = []

        if not dispatch_id:
            entry_errors.append("DISPATCH_ID_REQUIRED")
        else:
            dispatch_ids.append(dispatch_id)

        if not isinstance(sequence, int) or sequence < 1:
            entry_errors.append("SEQUENCE_INVALID")
        else:
            sequences.append(sequence)

        if status != "QUEUED":
            entry_errors.append("STATUS_NOT_QUEUED")

        if target != "PAPER":
            entry_errors.append("TARGET_NOT_PAPER")

        if not token_id:
            entry_errors.append("TOKEN_ID_REQUIRED")
        if not proposal_id:
            entry_errors.append("PROPOSAL_ID_REQUIRED")
        if len(payload_hash) != 64:
            entry_errors.append("ORDER_PAYLOAD_HASH_INVALID")
        if len(policy_hash) != 64:
            entry_errors.append("POLICY_HASH_INVALID")

        age_seconds = None
        stale = False
        try:
            queued_at = _parse_utc(entry.get("queued_at"))
            age_seconds = max(0.0, (current_time - queued_at).total_seconds())
            stale = age_seconds > maximum_entry_age_seconds
            if stale:
                warnings.append(f"STALE_ENTRY:{dispatch_id or 'UNKNOWN'}")
        except Exception:
            entry_errors.append("QUEUED_AT_INVALID")

        inspected_entries.append({
            "dispatch_id": dispatch_id,
            "sequence": sequence,
            "status": status,
            "age_seconds": age_seconds,
            "stale": stale,
            "entry_hash": canonical_hash(entry),
            "errors": entry_errors,
            "valid": not entry_errors,
        })

        for error in entry_errors:
            errors.append(f"{error}:{dispatch_id or 'UNKNOWN'}")

    if len(dispatch_ids) != len(set(dispatch_ids)):
        errors.append("DUPLICATE_DISPATCH_ID")

    if len(sequences) != len(set(sequences)):
        errors.append("DUPLICATE_SEQUENCE")

    if sequences and sequences != sorted(sequences):
        errors.append("FIFO_SEQUENCE_NOT_SORTED")

    expected_sequences = list(range(1, len(sequences) + 1))
    if sequences and sequences != expected_sequences:
        errors.append("FIFO_SEQUENCE_GAP")

    lock_active = lock.get("locked") is True
    if lock_active and not str(lock.get("owner", "")).strip():
        errors.append("LOCK_OWNER_REQUIRED")

    valid = not errors
    stale_count = sum(1 for item in inspected_entries if item["stale"])
    health_score = max(
        0,
        100
        - len(errors) * 20
        - stale_count * 10
        - (5 if lock_active else 0),
    )

    head_entry = inspected_entries[0] if inspected_entries else None
    release_ready = (
        valid
        and bool(entries)
        and not lock_active
        and stale_count == 0
        and head_entry is not None
        and head_entry["valid"]
    )

    if not valid:
        state = "QUEUE_INSPECTION_INVALID"
        action = "BLOCK_QUEUE_RELEASE"
    elif not entries:
        state = "QUEUE_INSPECTION_EMPTY"
        action = "WAIT_FOR_QUEUE_ENTRY"
    elif lock_active:
        state = "QUEUE_INSPECTION_LOCKED"
        action = "WAIT_FOR_QUEUE_UNLOCK"
    elif stale_count:
        state = "QUEUE_INSPECTION_STALE"
        action = "REVIEW_STALE_QUEUE_ENTRIES"
    else:
        state = "QUEUE_INSPECTION_READY"
        action = "ALLOW_RELEASE_AUTHORIZATION_STAGE"

    return {
        "state": state,
        "required_action": action,
        "valid": valid,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "entry_count": len(entries),
        "stale_entry_count": stale_count,
        "lock_active": lock_active,
        "queue_hash": canonical_hash(queue_state),
        "health_score": health_score,
        "release_ready": release_ready,
        "head_entry": head_entry,
        "inspected_entries": inspected_entries,
    }
