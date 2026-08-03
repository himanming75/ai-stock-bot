from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

def load_bars(path: Path) -> list[dict[str, float]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                close = float(row.get("close", row.get("Close", "")))
            except Exception:
                continue
            rows.append({"close": close})
    return rows

def slice_bars(
    bars: list[dict[str, float]],
    start_index: int,
    end_index: int,
) -> list[dict[str, float]]:
    end = end_index if end_index > 0 else len(bars)
    return bars[max(0, start_index):min(len(bars), end)]
