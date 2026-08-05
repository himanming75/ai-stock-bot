from __future__ import annotations

import json
from datetime import datetime
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


def normalized_equity_points(rows: list[dict]) -> list[dict]:
    points = []
    for row in rows:
        equity = D(row.get("equity"))
        generated_at = row.get("generated_at")
        if equity <= 0 or not generated_at:
            continue
        try:
            timestamp = datetime.fromisoformat(
                str(generated_at).replace("Z", "+00:00")
            )
        except ValueError:
            continue
        points.append(
            {
                "generated_at": timestamp.isoformat(),
                "timestamp": timestamp,
                "equity": equity,
                "daily_pl": D(row.get("daily_pl")),
                "daily_return_percent": D(
                    row.get("daily_return_percent")
                ),
            }
        )
    points.sort(key=lambda item: item["timestamp"])
    return points
