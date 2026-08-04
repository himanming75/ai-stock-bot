from __future__ import annotations
from typing import Any

def build_dashboard(
    modules: list[dict[str, Any]],
    pipeline: dict[str, Any],
    safety: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "system_status":"READY" if readiness.get("passed") else "REVIEW_REQUIRED",
        "readiness_score":readiness.get("readiness_score"),
        "readiness_level":readiness.get("readiness_level"),
        "ready_modules":readiness.get("ready_module_count"),
        "total_modules":readiness.get("module_count"),
        "pipeline_ready_steps":pipeline.get("ready_steps"),
        "pipeline_total_steps":pipeline.get("total_steps"),
        "safety_passed":safety.get("passed"),
        "module_rows":modules,
    }
