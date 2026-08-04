from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {}
    return v if isinstance(v,dict) else {}

def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8",newline="\n") as h:
        h.write(json.dumps(value,sort_keys=True)+"\n")

def digest(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
