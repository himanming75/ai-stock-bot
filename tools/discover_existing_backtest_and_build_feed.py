from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import ast, csv, hashlib, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

PATS=("backtest","historical","replay","simulation","simulator","alpaca_market_data","walk_forward","oos")
SKIP_PARTS={".git",".venv","venv","archive","__pycache__","node_modules"}
RESULT_HINTS=("trade","trades","result","results","backtest","closed","pnl","performance","ledger")
PNL_KEYS=("realized_pl","realized_pnl","pnl","profit","net_profit","pl")
SYMBOL_KEYS=("symbol","ticker")
ENTRY_KEYS=("entry_time","entry_time_utc","opened_at","created_at","timestamp")
EXIT_KEYS=("exit_time","exit_time_utc","closed_at","completed_at")
SIDE_KEYS=("side","entry_side","direction")
REASON_KEYS=("exit_reason","reason","close_reason")
CONF_KEYS=("confidence","score","signal_confidence")

def is_skipped(p:Path,root:Path):
    try: parts=p.relative_to(root).parts
    except Exception: return True
    return any(x in SKIP_PARTS for x in parts)

def sha256(p:Path):
    try:
        h=hashlib.sha256()
        with p.open("rb") as f:
            for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
        return h.hexdigest()
    except Exception:
        return None

def first(row,keys):
    for k in keys:
        if isinstance(row,dict) and row.get(k) not in (None,""):
            return row.get(k)
    return None

def f(v):
    try:return float(v)
    except Exception:return None

def pnl(row):
    return f(first(row,PNL_KEYS))

def normalize_trade(row,source):
    if not isinstance(row,dict): return None
    p=pnl(row)
    if p is None: return None
    sym=first(row,SYMBOL_KEYS)
    out={
        "symbol":str(sym).upper() if sym else None,
        "realized_pl":p,
        "entry_time":first(row,ENTRY_KEYS),
        "exit_time":first(row,EXIT_KEYS),
        "side":first(row,SIDE_KEYS),
        "exit_reason":first(row,REASON_KEYS),
        "confidence":first(row,CONF_KEYS),
        "_canonical_source":source,
    }
    # Preserve useful original fields without mutating source data.
    for k in ("entry_price","exit_price","qty","quantity","strategy","strategy_name","market_regime"):
        if row.get(k) not in (None,""):
            out[k]=row.get(k)
    return out

def extract_rows(p:Path):
    ext=p.suffix.lower()
    raw=[]
    try:
        if ext==".jsonl":
            for line in p.read_text(encoding="utf-8-sig",errors="replace").splitlines():
                if not line.strip(): continue
                try:
                    x=json.loads(line)
                    if isinstance(x,dict): raw.append(x)
                except Exception: pass
        elif ext==".json":
            x=json.loads(p.read_text(encoding="utf-8-sig",errors="replace"))
            if isinstance(x,list):
                raw=[r for r in x if isinstance(r,dict)]
            elif isinstance(x,dict):
                for key in ("trades","closed_trades","results","records","executions","round_trips"):
                    v=x.get(key)
                    if isinstance(v,list):
                        raw.extend(r for r in v if isinstance(r,dict))
        elif ext==".csv":
            with p.open("r",encoding="utf-8-sig",errors="replace",newline="") as h:
                raw=list(csv.DictReader(h))
    except Exception:
        return []
    source=str(p)
    return [n for r in raw if (n:=normalize_trade(r,source)) is not None]

def python_metadata(p:Path):
    meta={"path":str(p),"imports":[],"functions":[],"classes":[],"has_main":False,"cli_flags":[]}
    try:
        txt=p.read_text(encoding="utf-8-sig",errors="replace")
        tree=ast.parse(txt)
        for n in ast.walk(tree):
            if isinstance(n,(ast.Import,ast.ImportFrom)):
                if isinstance(n,ast.Import):
                    meta["imports"].extend(a.name for a in n.names)
                else:
                    meta["imports"].append(n.module or "")
            elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                meta["functions"].append(n.name)
            elif isinstance(n,ast.ClassDef):
                meta["classes"].append(n.name)
        meta["has_main"]="__main__" in txt
        meta["cli_flags"]=sorted(set(re.findall(r'--[A-Za-z0-9_-]+',txt)))[:100]
    except Exception as e:
        meta["parse_error"]=f"{type(e).__name__}: {e}"
    return meta

def discover(root:Path):
    files=[]
    for p in root.rglob("*"):
        if not p.is_file() or is_skipped(p,root): continue
        rel=str(p.relative_to(root)).replace("\\","/")
        low=rel.lower()
        if any(x in low for x in PATS):
            files.append(p)
    files.sort(key=lambda p:str(p).lower())
    return files

def candidate_result_files(root:Path):
    out=[]
    for p in root.rglob("*"):
        if not p.is_file() or is_skipped(p,root): continue
        if p.suffix.lower() not in {".json",".jsonl",".csv"}: continue
        low=str(p.relative_to(root)).lower()
        if not any(h in low for h in RESULT_HINTS): continue
        # Runtime/backtest/release outputs are more likely than configs/fixtures.
        if any(x in low for x in ("runtime","backtest","release","output","result","ledger")):
            out.append(p)
    return out

def build(root:Path):
    root=Path(root).resolve()
    discovered=discover(root)
    py=[python_metadata(p) for p in discovered if p.suffix.lower()==".py"]
    result_files=candidate_result_files(root)

    canonical=[]
    source_stats=[]
    seen=set()
    for p in result_files:
        rows=extract_rows(p)
        if not rows: continue
        sig=sha256(p)
        source_stats.append({
            "path":str(p.relative_to(root)).replace("\\","/"),
            "trade_rows":len(rows),
            "sha256":sig,
        })
        for r in rows:
            # dedup normalized records across copied release/runtime artifacts
            key=json.dumps({k:r.get(k) for k in ("symbol","realized_pl","entry_time","exit_time","side","exit_reason")},sort_keys=True,default=str)
            kh=hashlib.sha256(key.encode()).hexdigest()
            if kh in seen: continue
            seen.add(kh)
            r["_canonical_record_hash"]=kh
            canonical.append(r)

    out=root/"runtime/canonical_backtest_feed"
    out.mkdir(parents=True,exist_ok=True)
    feed=out/"canonical_backtest_trades.jsonl"
    with feed.open("w",encoding="utf-8") as h:
        for r in canonical:
            h.write(json.dumps(r,default=str)+"\n")

    likely_runners=[]
    for m in py:
        path=m["path"].replace("\\","/")
        names=" ".join(m["functions"]+m["classes"]).lower()
        if m["has_main"] and any(x in (path+" "+names).lower() for x in ("backtest","historical","replay","simulation")):
            likely_runners.append(m)

    report={
        "stage":"EXISTING_BACKTEST_DISCOVERY_CANONICAL_FEED_V1",
        "status":"PASS",
        "mode":"READ_ONLY_DISCOVERY_PLUS_DERIVED_FEED",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "discovered_backtest_historical_files":len(discovered),
        "python_components":len(py),
        "likely_existing_runners":likely_runners[:100],
        "result_sources_with_trade_rows":source_stats,
        "result_source_count":len(source_stats),
        "canonical_trade_count":len(canonical),
        "canonical_feed_path":"runtime/canonical_backtest_feed/canonical_backtest_trades.jsonl",
        "next_state":"CROSS_VALIDATION_FEED_READY" if canonical else "NEEDS_EXISTING_REPLAY_CONNECTION",
        "contracts":{
            "existing_source_files_modified":False,
            "new_backtest_engine_created":False,
            "new_strategy_created":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "task_change_performed":False,
            "paper_decision_path_changed":False,
            "live_decision_path_changed":False,
            "derived_runtime_feed_only":True,
        },
    }
    (out/"backtest_discovery_report.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    (out/"python_component_map.json").write_text(json.dumps(py,indent=2,default=str),encoding="utf-8")
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    args=p.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
