from __future__ import annotations
from typing import Any

def build_recovery_plan(
    modules: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    retry_limit = int(policy.get("retry_limit", 3))
    missing = [row["module_id"] for row in modules if not row.get("present")]
    not_ready = [
        row["module_id"]
        for row in modules
        if row.get("present") and not row.get("ready")
    ]
    actions = []
    for module_id in missing:
        actions.append({
            "module_id": module_id,
            "action": "RESTORE_SOURCE_ARTIFACT",
            "retry_limit": 0,
        })
    for module_id in not_ready:
        actions.append({
            "module_id": module_id,
            "action": "RERUN_AND_REVERIFY_MODULE",
            "retry_limit": retry_limit,
        })
    return {
        "recovery_required": bool(actions),
        "missing_modules": missing,
        "not_ready_modules": not_ready,
        "actions": actions,
    }
