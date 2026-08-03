from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Any

def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def normalize_bar(row: dict[str, Any]) -> dict[str, Any] | None:
    aliases = {
        "timestamp": ["timestamp","time","datetime","date","t"],
        "open": ["open","o"], "high": ["high","h"], "low": ["low","l"],
        "close": ["close","c","adj_close"], "volume": ["volume","v"]
    }
    out = {}
    for key, names in aliases.items():
        for name in names:
            if name in row:
                out[key] = row[name]
                break
    if not all(k in out for k in ("timestamp","open","high","low","close")):
        return None
    try:
        return {
            "timestamp": str(out["timestamp"]),
            "open": float(out["open"]), "high": float(out["high"]),
            "low": float(out["low"]), "close": float(out["close"]),
            "volume": float(out.get("volume", 0))
        }
    except (TypeError, ValueError):
        return None

def extract_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        for key in ("bars","data","rows","items","historical_bars"):
            if isinstance(value.get(key), list):
                return [x for x in value[key] if isinstance(x, dict)]
    return []

def load_bars(path: Path) -> list[dict[str, Any]]:
    rows = []
    suffix = path.suffix.lower()
    if suffix == ".json":
        rows = extract_rows(load_json(path))
    elif suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                if isinstance(item, dict): rows.append(item)
            except Exception:
                pass
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    bars = [bar for row in rows if (bar := normalize_bar(row))]
    unique = {}
    for bar in bars:
        unique[bar["timestamp"]] = bar
    return [unique[k] for k in sorted(unique)]
