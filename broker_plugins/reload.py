from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from broker_plugins.io import write_json

def build_plan(root: Path, plugin_ids: list[str]) -> dict[str, Any]:
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plugin_ids": plugin_ids,
        "steps": [
            "ENABLE_EMERGENCY_STOP",
            "STOP_NEW_READ_CYCLES",
            "VERIFY_PLUGIN_MANIFESTS",
            "VERIFY_API_COMPATIBILITY",
            "CLEAR_DISCOVERY_CACHE",
            "RELOAD_READ_ONLY_DESCRIPTORS",
            "RUN_PLUGIN_HEALTH_CHECK",
            "RESUME_READ_ONLY_CYCLES",
        ],
        "hot_reload_performed": False,
        "broker_write_enabled": False,
        "actual_live_orders_submitted": 0,
    }
    write_json(root / "release/v201_01_to_v205_64/actual/plugin_reload_plan.json", result)
    return result
