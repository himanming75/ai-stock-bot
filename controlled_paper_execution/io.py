import json
from pathlib import Path
def read_json(p):
    with Path(p).open("r",encoding="utf-8-sig") as f: v=json.load(f)
    if not isinstance(v,dict): raise ValueError("JSON_OBJECT_REQUIRED")
    return v
def write_json(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def append_jsonl(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8",newline="\n") as f: f.write(json.dumps(v,sort_keys=True)+"\n")
