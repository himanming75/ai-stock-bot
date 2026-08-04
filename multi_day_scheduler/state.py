from __future__ import annotations
from typing import Any

def resolve_scheduler_state(
    source_cycle: dict[str, Any],
    queue_summary: dict[str, Any],
    duplicate: dict[str, Any],
) -> dict[str, Any]:
    if source_cycle.get("state") not in {
        "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL",
        "AUTONOMOUS_CYCLE_HOLD",
        "AUTONOMOUS_CYCLE_REVIEW_REQUIRED",
        "AUTONOMOUS_CYCLE_BLOCKED",
    }:
        return {
            "state":"MULTI_DAY_SCHEDULER_SOURCE_REQUIRED",
            "action":"BLOCK_SCHEDULER",
        }
    if not duplicate.get("passed"):
        return {
            "state":"MULTI_DAY_SCHEDULER_DUPLICATE_REVIEW_REQUIRED",
            "action":"REVIEW_DUPLICATE_SESSIONS",
        }
    if queue_summary.get("session_count",0)<=0:
        return {
            "state":"MULTI_DAY_SCHEDULER_NO_SESSIONS",
            "action":"NO_ACTION",
        }
    return {
        "state":"MULTI_DAY_SCHEDULER_READY",
        "action":"QUEUE_TRADING_SESSIONS",
    }
