import json
from pathlib import Path
def load_json(path):
    if not Path(path).exists(): return {}
    try:
        v=json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return v if isinstance(v,dict) else {}
    except Exception: return {}
def write_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def append_jsonl(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8",newline="\n") as h: h.write(json.dumps(value,sort_keys=True)+"\n")
