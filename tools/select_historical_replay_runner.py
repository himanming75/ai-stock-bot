from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import ast, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

KEYWORDS={
    "historical":6,
    "backtest":6,
    "replay":7,
    "offline":4,
    "candidate":3,
    "multi_asset":3,
    "walk_forward":2,
    "oos":2,
    "alpaca_market_data":2,
}
SAFE_NEGATIVE={
    "submit_order":-20,
    "place_order":-20,
    "cancel_order":-8,
    "TradingClient(": -8,
    "live_trading":-10,
}
OUTPUT_HINTS=("jsonl","json","csv","trade","result","ledger","output","report")
SKIP={".git",".venv","venv","archive","__pycache__","node_modules","runtime"}

def skipped(p:Path,root:Path):
    try:
        parts=p.relative_to(root).parts
    except Exception:
        return True
    return any(x in SKIP for x in parts)

def py_info(p:Path,root:Path):
    rel=str(p.relative_to(root)).replace("\\","/")
    try:
        txt=p.read_text(encoding="utf-8-sig",errors="replace")
    except Exception:
        return None

    low=(rel+"\n"+txt[:40000]).lower()
    if not any(k in low for k in KEYWORDS):
        return None

    info={
        "path":rel,
        "functions":[],
        "classes":[],
        "imports":[],
        "cli_flags":sorted(set(re.findall(r'--[A-Za-z0-9_-]+',txt))),
        "literal_paths":sorted(set(re.findall(r'["\']([^"\']+\.(?:jsonl|json|csv|parquet))["\']',txt,re.I)))[:100],
        "has_main":"__main__" in txt,
        "danger_markers":[],
        "output_hints":[],
        "score":0,
    }

    try:
        tree=ast.parse(txt)
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                info["functions"].append(n.name)
            elif isinstance(n,ast.ClassDef):
                info["classes"].append(n.name)
            elif isinstance(n,ast.Import):
                info["imports"].extend(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):
                info["imports"].append(n.module or "")
    except Exception as exc:
        info["parse_error"]=f"{type(exc).__name__}: {exc}"

    score=0
    for k,w in KEYWORDS.items():
        if k in low:
            score+=w

    if info["has_main"]:
        score+=4
    if info["cli_flags"]:
        score+=3
    if any(x in low for x in ("historical bars","historical_bars","historical_data")):
        score+=5
    if any(x in low for x in ("closed_trades","realized_pl","realized_pnl","trade_results")):
        score+=6
    if any(x in low for x in ("strategy","signal","candidate")):
        score+=3
    if any(x in low for x in ("start_date","end_date","start-date","end-date","symbol","symbols")):
        score+=3

    for marker,penalty in SAFE_NEGATIVE.items():
        if marker.lower() in low:
            info["danger_markers"].append(marker)
            score+=penalty

    for h in OUTPUT_HINTS:
        if h in low:
            info["output_hints"].append(h)

    if "/test" in rel.lower() or rel.lower().startswith("test") or "test_" in p.name.lower():
        score-=12
    if "/tools/" in "/"+rel.lower() or rel.lower().startswith("tools/"):
        score+=2

    info["score"]=score
    info["recommended_for_execution"]=(
        score>=12 and info["has_main"] and len(info["danger_markers"])==0
    )
    return info

def ps_info(p:Path,root:Path):
    rel=str(p.relative_to(root)).replace("\\","/")
    try:
        txt=p.read_text(encoding="utf-8-sig",errors="replace")
    except Exception:
        return None

    low=(rel+"\n"+txt).lower()
    if not any(k in low for k in KEYWORDS):
        return None

    calls=sorted(set(re.findall(r'(?:python|python\.exe|\.\\\.venv\\scripts\\python\.exe)\s+([^\r\n]+)',txt,re.I)))
    return {"path":rel,"python_calls":calls[:50]}

def build(root:Path):
    root=Path(root).resolve()
    py=[]
    ps=[]

    for p in root.rglob("*"):
        if not p.is_file() or skipped(p,root):
            continue
        if p.suffix.lower()==".py":
            x=py_info(p,root)
            if x:
                py.append(x)
        elif p.suffix.lower()==".ps1":
            x=ps_info(p,root)
            if x:
                ps.append(x)

    py.sort(key=lambda x:(x["score"],x["path"]),reverse=True)
    safe=[x for x in py if x["recommended_for_execution"]]
    top=safe[:10] if safe else [x for x in py if x["score"]>0][:10]

    recommendations=[]
    for rank,x in enumerate(top[:5],1):
        recommendations.append({
            "rank":rank,
            "path":x["path"],
            "score":x["score"],
            "cli_flags":x["cli_flags"],
            "literal_paths":x["literal_paths"],
            "imports":x["imports"][:30],
            "functions":x["functions"][:50],
            "classes":x["classes"][:20],
            "danger_markers":x["danger_markers"],
            "recommended_for_execution":x["recommended_for_execution"],
            "execution_contract":{
                "invoke_only_after_manual_review":True,
                "broker_write_must_remain_false":True,
                "live_write_must_remain_false":True,
                "output_trade_schema_required":["symbol","realized_pl","entry_time","exit_time"],
                "source_provenance_required":True,
            },
        })

    out=root/"runtime/historical_replay_runner_selection"
    out.mkdir(parents=True,exist_ok=True)

    report={
        "stage":"HISTORICAL_REPLAY_RUNNER_SELECTION_V1_1",
        "status":"PASS",
        "mode":"STATIC_READ_ONLY_AUDIT",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "python_candidate_count":len(py),
        "powershell_candidate_count":len(ps),
        "safe_execution_candidate_count":len(safe),
        "recommended_candidates":recommendations,
        "all_python_candidates":py[:100],
        "powershell_runner_map":ps[:100],
        "selection_status":"READY_FOR_HISTORICAL_REPLAY_IMPLEMENTATION" if recommendations else "NO_SAFE_EXISTING_RUNNER_FOUND",
        "contracts":{
            "candidate_runner_executed":False,
            "existing_source_modified":False,
            "paper_task_modified":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "new_backtest_engine_created":False,
            "new_strategy_created":False,
            "live_auto_enable":False,
        },
    }

    (out/"latest_runner_selection.json").write_text(
        json.dumps(report,indent=2,default=str),
        encoding="utf-8"
    )
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    args=p.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
