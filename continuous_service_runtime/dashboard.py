from __future__ import annotations
from pathlib import Path
from continuous_service_runtime.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v104_33_to_v104_64/actual/"
        "continuous_service_runtime_result.json"
    )
    return {
        "state": result.get("state", "NOT_AVAILABLE"),
        "runtime_id": result.get("runtime_id"),
        "tick_count": result.get("tick_count"),
        "heartbeat_count": result.get("heartbeat_count"),
        "scheduler_ticks": result.get("scheduler_ticks", []),
        "checkpoint": result.get("checkpoint", {}),
        "recovery": result.get("recovery", {}),
        "shutdown": result.get("shutdown", {}),
        "background_service_running": False,
        "execution_authorized": False,
        "paper_only": True,
    }
