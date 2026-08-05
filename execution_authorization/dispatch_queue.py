from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


VALID_STATUSES = {"QUEUED", "LOCKED", "RELEASED", "CANCELED"}


def validate_queue_state(queue_state: dict[str, Any]) -> dict[str, Any]:
    entries = queue_state.get("entries", [])
    lock = queue_state.get("lock", {})

    errors: list[str] = []

    if not isinstance(entries, list):
        errors.append("ENTRIES_MUST_BE_LIST")
        entries = []

    dispatch_ids: list[str] = []
    sequence_numbers: list[int] = []

    for entry in entries:
        dispatch_id = str(entry.get("dispatch_id", "")).strip()
        status = str(entry.get("status", "")).strip()
        sequence = entry.get("sequence")

        if not dispatch_id:
            errors.append("DISPATCH_ID_REQUIRED")
        else:
            dispatch_ids.append(dispatch_id)

        if status not in VALID_STATUSES:
            errors.append(f"INVALID_STATUS:{dispatch_id or 'UNKNOWN'}")

        if not isinstance(sequence, int) or sequence < 1:
            errors.append(f"INVALID_SEQUENCE:{dispatch_id or 'UNKNOWN'}")
        else:
            sequence_numbers.append(sequence)

    if len(dispatch_ids) != len(set(dispatch_ids)):
        errors.append("DUPLICATE_DISPATCH_ID")

    if len(sequence_numbers) != len(set(sequence_numbers)):
        errors.append("DUPLICATE_SEQUENCE")

    if sequence_numbers and sequence_numbers != sorted(sequence_numbers):
        errors.append("SEQUENCE_NOT_SORTED")

    if not isinstance(lock, dict):
        errors.append("LOCK_MUST_BE_OBJECT")
        lock = {}

    if lock.get("locked") is True and not str(lock.get("owner", "")).strip():
        errors.append("LOCK_OWNER_REQUIRED")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "entry_count": len(entries),
        "dispatch_ids": dispatch_ids,
        "sequence_numbers": sequence_numbers,
        "lock": lock,
    }


def enqueue_dispatch(
    queue_state: dict[str, Any],
    preparation_result: dict[str, Any],
    owner: str,
) -> dict[str, Any]:
    validation = validate_queue_state(queue_state)
    if not validation["valid"]:
        return {
            "approved": False,
            "state": "DISPATCH_QUEUE_INVALID",
            "failed": validation["errors"],
            "queue_state": queue_state,
            "queue_validation": validation,
            "required_action": "REPAIR_QUEUE_BEFORE_ENQUEUE",
        }

    if not owner.strip():
        return {
            "approved": False,
            "state": "DISPATCH_QUEUE_LOCK_REJECTED",
            "failed": ["LOCK_OWNER_REQUIRED"],
            "queue_state": queue_state,
            "queue_validation": validation,
            "required_action": "PROVIDE_LOCK_OWNER",
        }

    if queue_state.get("lock", {}).get("locked") is True:
        return {
            "approved": False,
            "state": "DISPATCH_QUEUE_LOCKED",
            "failed": ["QUEUE_ALREADY_LOCKED"],
            "queue_state": queue_state,
            "queue_validation": validation,
            "required_action": "WAIT_FOR_QUEUE_UNLOCK",
        }

    evaluation = preparation_result.get("evaluation", {})
    dispatch_id = str(evaluation.get("dispatch_id", "")).strip()
    token_id = str(evaluation.get("token_id", "")).strip()
    proposal_id = str(evaluation.get("proposal_id", "")).strip()

    checks = {
        "preparation_stage_valid": preparation_result.get("stage") == "V392.03A",
        "preparation_status_pass": preparation_result.get("status") == "PASS",
        "preparation_ready": (
            preparation_result.get("state") == "DISPATCH_PREPARATION_GATE_READY"
        ),
        "preparation_approved": (
            preparation_result.get("dispatch_preparation_approved") is True
        ),
        "queue_entry_allowed": preparation_result.get("queue_entry_allowed") is True,
        "dispatch_id_present": bool(dispatch_id),
        "token_id_present": bool(token_id),
        "proposal_id_present": bool(proposal_id),
        "dispatch_not_present": dispatch_id not in set(validation["dispatch_ids"]),
        "dispatch_execution_disabled": (
            preparation_result.get("dispatch_execution_allowed") is False
        ),
        "paper_submission_disabled": (
            preparation_result.get("paper_submission_enabled") is False
        ),
        "live_submission_disabled": (
            preparation_result.get("live_submission_enabled") is False
        ),
        "broker_write_disabled": (
            preparation_result.get("broker_write_enabled") is False
        ),
    }

    approved = all(checks.values())
    if not approved:
        return {
            "approved": False,
            "state": "DISPATCH_QUEUE_ENQUEUE_REJECTED",
            "checks": checks,
            "failed": [name for name, passed in checks.items() if not passed],
            "queue_state": queue_state,
            "queue_validation": validation,
            "required_action": "DO_NOT_ENQUEUE_DISPATCH",
        }

    now = datetime.now(timezone.utc).isoformat()
    next_sequence = max(validation["sequence_numbers"], default=0) + 1
    new_entry = {
        "dispatch_id": dispatch_id,
        "token_id": token_id,
        "proposal_id": proposal_id,
        "sequence": next_sequence,
        "status": "QUEUED",
        "queued_at": now,
        "order_payload_hash": evaluation.get("order_payload_hash"),
        "policy_hash": evaluation.get("policy_hash"),
        "target_environment": "PAPER",
    }

    updated_entries = list(queue_state.get("entries", []))
    updated_entries.append(new_entry)

    updated_queue = {
        "queue_version": "V392.04A",
        "entries": updated_entries,
        "lock": {
            "locked": False,
            "owner": "",
            "locked_at": None,
        },
        "updated_at": now,
    }

    return {
        "approved": True,
        "state": "DISPATCH_QUEUE_ENTRY_CREATED",
        "checks": checks,
        "failed": [],
        "entry": new_entry,
        "queue_state": updated_queue,
        "queue_validation": validate_queue_state(updated_queue),
        "required_action": "ALLOW_QUEUE_INSPECTION_STAGE",
    }
