from __future__ import annotations
from typing import Any
from autonomous_cycle.retry import can_retry

def execute_step(
    step: dict[str, Any],
    context: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    item = dict(step)
    item["attempt_count"] = int(item.get("attempt_count", 0)) + 1
    step_id = item["step_id"]

    passed = True
    error = None

    if step_id == "VALIDATE_SOURCE_DECISION":
        passed = context.get("source_status") == "PASS"
        error = None if passed else "SOURCE_DECISION_STATUS_INVALID"

    elif step_id == "ACQUIRE_CYCLE_LOCK":
        passed = context.get("lock_acquired") is True
        error = None if passed else "CYCLE_LOCK_NOT_ACQUIRED"

    elif step_id == "CREATE_CYCLE_CHECKPOINT":
        passed = context.get("checkpoint_enabled") is True
        error = None if passed else "CHECKPOINT_DISABLED"

    elif step_id == "EVALUATE_APPROVAL_REQUIREMENT":
        passed = context.get("manual_approval_required") is True
        error = None if passed else "MANUAL_APPROVAL_GUARD_MISSING"

    elif step_id == "PREPARE_PAPER_ACTION_PLAN":
        passed = (
            context.get("paper_only") is True
            and context.get("actual_orders_submitted") == 0
        )
        error = None if passed else "PAPER_SAFETY_VIOLATION"

    elif step_id == "FINALIZE_CYCLE_STATE":
        passed = context.get("final_state") is not None
        error = None if passed else "FINAL_STATE_NOT_RESOLVED"

    if passed:
        item["state"] = "COMPLETED"
        item["error"] = None
    else:
        retry = can_retry(item["attempt_count"], policy)
        item["state"] = "RETRY_PENDING" if retry["retry_allowed"] else "FAILED"
        item["error"] = error

    return item
