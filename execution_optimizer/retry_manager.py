from __future__ import annotations
from typing import Any

def build(plan: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "retry_limit": int(policy["retry_limit"]),
        "retry_delay_seconds": int(policy["retry_delay_seconds"]),
        "partial_fill_timeout_seconds": int(policy["partial_fill_timeout_seconds"]),
        "cancel_replace_enabled": plan.get("order_type") == "LIMIT",
        "duplicate_prevention_required": True,
        "broker_submission_step_included": False,
        "steps": [
            "MONITOR_ORDER_STATE",
            "WAIT_FOR_FILL",
            "CHECK_PARTIAL_FILL",
            "CANCEL_IF_TIMEOUT",
            "REPRICE_WITHIN_LIMIT",
            "STOP_AFTER_RETRY_LIMIT",
        ],
    }
