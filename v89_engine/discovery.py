from __future__ import annotations
from pathlib import Path
from typing import Any
from v89_engine.io import load_bars

SEARCH_ROOTS = ("alpaca_market_data","historical","data","release")
EXTENSIONS = {".json",".jsonl",".csv"}

def discover_historical_files(root: Path, minimum_bars: int = 30) -> dict[str, Any]:
    candidates = []
    for folder in SEARCH_ROOTS:
        base = root / folder
        if not base.exists(): continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS: continue
            name = path.name.lower()
            if any(x in name for x in ("result","manifest","policy","certificate","ledger","state")):
                continue
            try:
                bars = load_bars(path)
            except Exception:
                continue
            if len(bars) >= minimum_bars:
                candidates.append({
                    "path": str(path.resolve()),
                    "relative_path": str(path.relative_to(root)),
                    "bar_count": len(bars),
                    "first_timestamp": bars[0]["timestamp"],
                    "last_timestamp": bars[-1]["timestamp"],
                })
    candidates.sort(key=lambda x: (-x["bar_count"], x["relative_path"]))
    return {"candidate_count": len(candidates), "candidates": candidates,
            "selected": candidates[0] if candidates else None}
