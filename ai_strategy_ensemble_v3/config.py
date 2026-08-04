from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from ai_strategy_ensemble_v3.io import load_json, write_json

DEFAULT = {
    "minimum_strategy_score": 55.0,
    "minimum_final_confidence": 65.0,
    "maximum_active_strategies": 4,
    "maximum_single_strategy_weight_pct": 50.0,
    "minimum_observations": 10,
    "risk_gate_required": True,
    "exit_conflict_blocks_entry": True,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False,
}

def path(root: Path) -> Path:
    return root / "release/v246_01_to_v250_64/config/ai_strategy_ensemble_v3_policy.json"

def load(root: Path) -> dict:
    value = load_json(path(root))
    if not value:
        value = deepcopy(DEFAULT)
        value["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(path(root), value)
    return value

def validate(value: dict) -> dict:
    errors = []
    normalized = deepcopy(DEFAULT)
    normalized.update(value)
    for key in ("paper_submission_enabled", "live_submission_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
        normalized[key] = False
    if int(value.get("maximum_active_strategies", 0) or 0) < 1:
        errors.append("maximum_active_strategies must be positive.")
    return {"valid": not errors, "errors": errors, "normalized": normalized}
