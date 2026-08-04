from __future__ import annotations
from typing import Any

def build_recovery(
    runtime_state: str,
    errors: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "recovery_required": bool(errors),
        "runtime_state": runtime_state,
        "errors": errors,
        "maximum_recovery_attempts": int(
            policy.get("maximum_recovery_attempts", 3)
        ),
        "actions": [
            {
                "error": error,
                "action": "RESTORE_RUNTIME_CHECKPOINT",
            }
            for error in errors
        ],
    }
