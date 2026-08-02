from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def load_dashboard_sources(root: Path) -> dict[str, dict[str, Any]]:
    return {
        "runtime": load_json(
            root / "release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json"
        ),
        "daily_report": load_json(
            root / "release/op2_17_to_op2_20/actual/daily_shadow_report.json"
        ),
        "heartbeat": load_json(
            root / "release/op2_17_to_op2_20/actual/shadow_runtime_heartbeat.json"
        ),
        "signal": load_json(
            root / "release/op2_13_to_op2_16/actual/generated_shadow_signal.json"
        ),
        "pipeline": load_json(
            root / "release/op2_13_to_op2_16/actual/automatic_shadow_signal_pipeline_result.json"
        ),
        "portfolio": load_json(
            root / "release/op1_13_to_op1_16/actual/current_paper_snapshot.json"
        ),
    }
