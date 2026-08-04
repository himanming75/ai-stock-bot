from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def load_json(path:Path)->dict[str,Any]:
    if not path.exists(): return {}
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value,dict) else {}

def write_json(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def append_jsonl(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(value,sort_keys=True)+"\n")
