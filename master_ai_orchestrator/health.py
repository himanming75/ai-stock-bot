from __future__ import annotations
from typing import Any

def evaluate_health(
    modules: list[dict[str, Any]],
    dependencies: dict[str, Any],
    workflow: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, Any]:
    required = [row for row in modules if row.get("required")]
    ready = [row for row in required if row.get("ready")]
    module_readiness_pct = (
        len(ready) / len(required) * 100.0 if required else 0.0
    )
    checks = {
        "required_modules_ready": len(ready) == len(required),
        "dependencies_passed": dependencies.get("passed") is True,
        "workflow_passed": workflow.get("passed") is True,
        "safety_passed": safety.get("passed") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
        "required_module_count": len(required),
        "ready_module_count": len(ready),
        "module_readiness_pct": round(module_readiness_pct, 6),
        "heartbeat_status": "HEALTHY" if not failed else "DEGRADED",
    }
