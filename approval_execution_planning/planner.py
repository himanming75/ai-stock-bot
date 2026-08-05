from __future__ import annotations
import hashlib
import json
from .models import D, text

def build_plan(allocation: dict, policy: dict) -> dict:
    symbol = str(allocation.get("symbol"))
    side = str(allocation.get("side"))
    notional = D(allocation.get("proposed_notional"))
    child_count = max(1, int(policy.get("child_order_count", 3)))
    child_notional = notional / child_count

    children = []
    for index in range(1, child_count + 1):
        amount = child_notional
        if index == child_count:
            amount = notional - child_notional * (child_count - 1)
        children.append(
            {
                "sequence": index,
                "symbol": symbol,
                "side": side,
                "planned_notional": text(amount),
                "order_type": policy.get("default_order_type", "limit"),
                "time_in_force": policy.get("time_in_force", "day"),
                "submission_enabled": False,
                "order_ticket_created": False,
            }
        )

    seed = {
        "symbol": symbol,
        "side": side,
        "notional": text(notional),
        "children": children,
    }
    fingerprint = hashlib.sha256(
        json.dumps(seed, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "plan_id": f"execplan_{fingerprint[:24]}",
        "plan_fingerprint": fingerprint,
        "symbol": symbol,
        "side": side,
        "parent_notional": text(notional),
        "child_order_count": child_count,
        "child_orders": children,
        "retry_policy": {
            "maximum_attempts": int(policy.get("maximum_retry_attempts", 2)),
            "backoff_seconds": int(policy.get("retry_backoff_seconds", 5)),
            "automatic_retry_enabled": False,
        },
        "cancel_policy": {
            "automatic_cancel_enabled": False,
            "cancel_after_seconds": int(
                policy.get("cancel_after_seconds", 120)
            ),
        },
        "replace_policy": {
            "automatic_replace_enabled": False,
            "maximum_replacements": int(
                policy.get("maximum_replacements", 1)
            ),
        },
        "partial_fill_policy": {
            "monitor_only": True,
            "automatic_followup_enabled": False,
        },
        "recovery_policy": {
            "checkpoint_required": True,
            "resume_requires_reapproval": True,
        },
        "order_ticket_created": False,
        "submission_enabled": False,
    }
