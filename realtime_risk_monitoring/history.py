from __future__ import annotations

import json
from pathlib import Path

from .models import D


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"INVALID_JSONL:{path}:{line_number}:{exc}"
            ) from exc
    return rows


def equity_history(metrics_rows: list[dict], current_equity) -> list:
    values = []
    for row in metrics_rows:
        value = D(row.get("equity"))
        if value > 0:
            values.append(value)
    current = D(current_equity)
    if current > 0:
        values.append(current)
    return values
