from __future__ import annotations
from typing import Any

WRITE_METHODS = {
    "submit_order",
    "cancel_order",
    "replace_order",
    "close_position",
    "close_all_positions",
    "transfer_funds",
}

def validate_safe_boundary(capabilities: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "read_only": capabilities.get("read_only") is True,
        "order_submit_disabled": capabilities.get("order_submit") is False,
        "order_cancel_disabled": capabilities.get("order_cancel") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
        "blocked_write_methods": sorted(WRITE_METHODS),
    }

def block_write(method_name: str) -> None:
    if method_name in WRITE_METHODS:
        raise PermissionError(
            f"Blocked broker write method: {method_name}"
        )
