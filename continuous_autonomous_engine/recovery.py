from __future__ import annotations
from typing import Any

def build_recovery(
    source_validation: dict[str, Any],
    failed_phases: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    actions=[]
    for source in source_validation.get("failed",[]):
        actions.append({
            "type":"SOURCE_RECOVERY",
            "target":source,
            "action":"RERUN_AND_VERIFY_SOURCE_STAGE",
        })
    for phase in failed_phases:
        actions.append({
            "type":"PHASE_RECOVERY",
            "target":phase,
            "action":"RESUME_FROM_CHECKPOINT",
        })
    return {
        "recovery_required":bool(actions),
        "maximum_recovery_attempts":int(
            policy.get("maximum_recovery_attempts",3)
        ),
        "actions":actions,
    }
