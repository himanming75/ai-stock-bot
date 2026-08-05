import json
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def append_jsonl(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(value,sort_keys=True)+"\n")
