from __future__ import annotations
from pathlib import Path
from typing import Any

def discover_datasets(root: Path, policy: dict[str, Any]) -> list[dict[str, Any]]:
    configured = policy.get("datasets", [])
    rows = []
    for item in configured:
        path = root / str(item.get("path", ""))
        rows.append({
            "dataset_id": str(item.get("dataset_id", path.stem)),
            "symbol": str(item.get("symbol", "UNKNOWN")).upper(),
            "path": str(path),
            "exists": path.exists(),
        })
    return rows

def discover_strategies(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in policy.get("strategies", []):
        if item.get("enabled", True):
            rows.append({
                "strategy_id": str(item.get("strategy_id")),
                "family": str(item.get("family", "GENERIC")).upper(),
                "parameters": dict(item.get("parameters", {})),
            })
    return rows
