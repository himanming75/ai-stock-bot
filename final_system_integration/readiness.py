from __future__ import annotations
from typing import Any

def calculate_readiness(
    modules: list[dict[str, Any]],
    pipeline: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, Any]:
    ready_count=sum(1 for row in modules if row.get("ready"))
    module_count=len(modules)
    module_pct=ready_count/module_count*100.0 if module_count else 0.0
    pipeline_pct=(
        pipeline.get("ready_steps",0)/max(1,pipeline.get("total_steps",0))*100.0
    )
    safety_pct=100.0 if safety.get("passed") else 0.0
    score=module_pct*0.5+pipeline_pct*0.3+safety_pct*0.2
    if score>=95:
        level="READY"
    elif score>=80:
        level="REVIEW"
    else:
        level="NOT_READY"
    return {
        "readiness_score":round(score,6),
        "readiness_level":level,
        "module_count":module_count,
        "ready_module_count":ready_count,
        "module_readiness_pct":round(module_pct,6),
        "pipeline_readiness_pct":round(pipeline_pct,6),
        "safety_readiness_pct":round(safety_pct,6),
        "passed":level=="READY",
    }
