from __future__ import annotations
import hashlib,json
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
    with path.open("a",encoding="utf-8",newline="\n") as h:
        h.write(json.dumps(value,sort_keys=True)+"\n")

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()
