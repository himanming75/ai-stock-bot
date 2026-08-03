import json
from pathlib import Path


def build_performance_production_readiness_payload(root: Path):
    path = (
        root / "release/v83_89_to_v83_96/actual/"
        "performance_production_readiness_dashboard_state.json"
    )
    if not path.exists():
        return {"performance_production_readiness_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"performance_production_readiness_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "performance_production_readiness_state": "NOT_AVAILABLE"
    }
