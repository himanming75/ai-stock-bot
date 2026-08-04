from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from multi_timeframe_strategy.io import load_json, write_json

DEFAULT = {
    "profiles": {
        "SCALP": {
            "enabled": True,
            "timeframes": ["1m", "3m", "5m"],
            "maximum_holding_minutes": 30,
            "risk_per_trade_pct": 0.25,
            "capital_weight_pct": 25.0,
            "minimum_confidence": 70.0
        },
        "DAY": {
            "enabled": True,
            "timeframes": ["5m", "15m", "30m"],
            "maximum_holding_minutes": 390,
            "risk_per_trade_pct": 0.50,
            "capital_weight_pct": 45.0,
            "minimum_confidence": 65.0
        },
        "SWING": {
            "enabled": True,
            "timeframes": ["1h", "4h", "1d"],
            "maximum_holding_minutes": 10080,
            "risk_per_trade_pct": 0.75,
            "capital_weight_pct": 30.0,
            "minimum_confidence": 60.0
        }
    },
    "maximum_total_risk_pct": 1.50,
    "allow_same_symbol_across_profiles": False,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False
}

def path(root: Path) -> Path:
    return root / "release/v271_01_to_v280_64/config/multi_timeframe_strategy_policy.json"

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
            errors.append(f"{key} must remain false.")
        normalized[key] = False
    total_weight = sum(
        float(profile.get("capital_weight_pct", 0) or 0)
        for profile in value.get("profiles", {}).values()
        if profile.get("enabled")
    )
    if round(total_weight, 6) != 100.0:
        errors.append("Enabled profile capital weights must total 100%.")
    return {"valid": not errors, "errors": errors, "normalized": normalized}
