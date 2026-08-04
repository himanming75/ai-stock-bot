from __future__ import annotations
from typing import Any

BLOCKED_METHODS = [
    "submit_order",
    "cancel_order",
    "replace_order",
    "close_position",
    "close_all_positions",
    "transfer_funds",
]

def evaluate_boundary(capabilities: dict[str, Any]) -> dict[str, Any]:
    checks={
        "read_only":capabilities.get("read_only") is True,
        "submit_disabled":capabilities.get("order_submit") is False,
        "cancel_disabled":capabilities.get("order_cancel") is False,
        "replace_disabled":capabilities.get("order_replace") is False,
        "fund_transfer_disabled":capabilities.get("fund_transfer") is False,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "blocked_methods":BLOCKED_METHODS,
    }
