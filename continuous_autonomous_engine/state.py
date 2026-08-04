from __future__ import annotations
from typing import Any

def resolve_state(
    source_validation: dict[str, Any],
    selected_session: dict[str, Any],
    gates: dict[str, Any],
    failed_phases: list[str],
    cycle_state: str | None,
) -> dict[str, Any]:
    if not source_validation.get("passed"):
        return {
            "state":"CONTINUOUS_AUTONOMOUS_ENGINE_SOURCE_REQUIRED",
            "action":"RESTORE_SOURCES",
        }
    if not selected_session.get("session_available"):
        return {
            "state":"CONTINUOUS_AUTONOMOUS_ENGINE_IDLE",
            "action":"WAIT_FOR_SESSION",
        }
    if failed_phases:
        return {
            "state":"CONTINUOUS_AUTONOMOUS_ENGINE_RECOVERY_REQUIRED",
            "action":"RESUME_FROM_CHECKPOINT",
        }
    if not gates.get("passed"):
        return {
            "state":"CONTINUOUS_AUTONOMOUS_ENGINE_GATE_BLOCKED",
            "action":"BLOCK_ITERATION",
        }
    if cycle_state=="AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL":
        return {
            "state":"CONTINUOUS_AUTONOMOUS_ENGINE_WAITING_FOR_MANUAL_APPROVAL",
            "action":"WAIT_FOR_MANUAL_APPROVAL",
        }
    if cycle_state=="AUTONOMOUS_CYCLE_HOLD":
        return {
            "state":"CONTINUOUS_AUTONOMOUS_ENGINE_HOLD",
            "action":"NO_ACTION",
        }
    return {
        "state":"CONTINUOUS_AUTONOMOUS_ENGINE_READY",
        "action":"PAPER_CONTEXT_READY",
    }
