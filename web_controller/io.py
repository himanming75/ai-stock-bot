from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value,dict) else {}

def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def tail_jsonl(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines()[-limit:]:
        try:
            value=json.loads(line)
            if isinstance(value,dict):
                rows.append(value)
        except Exception:
            continue
    return rows
