from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from strategy_engine_v2.models import SignalInput


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_signals(payload: dict[str, Any]) -> tuple[str, list[SignalInput]]:
    symbol = str(payload.get("symbol", "UNKNOWN"))
    rows = payload.get("signals", [])
    if not isinstance(rows, list):
        rows = []

    signals = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        signals.append(
            SignalInput(
                name=str(row.get("name", "signal")),
                score=float(row.get("score", 0.0)),
                weight=float(row.get("weight", 1.0)),
                enabled=bool(row.get("enabled", True)),
                reason=str(row.get("reason", "")),
            )
        )
    return symbol, signals
