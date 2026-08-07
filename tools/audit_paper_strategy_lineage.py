from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

TARGET_REPORT="multi_timeframe_ai_report_bilingual.json"
TERMS=(
    "multi_timeframe_ai_report_bilingual.json",
    "confidence_calibration",
    "calibrated_confidence",
    "reward_risk",
    "consensus_score",
    "\"analyses\"",
)
SKIP={".git",".venv","venv","archive","__pycache__","node_modules","runtime"}
DANGER=("submit_order(","TradingClient(","place_order(","cancel_order(")

def skip(p:Path,root:Path):
    try: parts=p.relative_to(root).parts
    except Exception: return True
    return any(x in SKIP for x in parts)

def text(path):
    try:return path.read_text(encoding="utf-8-sig",errors="replace")
    except Exception:return ""

def inspect_python(p:Path,root:Path):
    rel=str(p.relative_to(root)).replace("\\","/")
    txt=text(p)
    if not txt:return None
    hits=[t for t in TERMS if t.lower() in txt.lower()]
    if not hits:return None

    functions=[];classes=[];imports=[]
    parse_ok=True
    try:
        tree=ast.parse(txt)
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):functions.append(n.name)
            elif isinstance(n,ast.ClassDef):classes.append(n.name)
            elif isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):imports.append(n.module or "")
    except Exception:
        parse_ok=False

    low=txt.lower()
    writes_target=(
        TARGET_REPORT.lower() in low
        and any(x in low for x in ("write_text","json.dump","write_json","open("))
    )
    producer_fields=sum(1 for t in ("analyses","confidence_calibration","reward_risk","consensus_score") if t in low)
    runnerish=("__main__" in txt or "argparse" in low)
    historical_input=any(x in low for x in ("historical","ohlcv","bars","timeframe","market_data"))
    dangerous=[d for d in DANGER if d.lower() in low]

    score=0
    score+=20 if writes_target else 0
    score+=producer_fields*5
    score+=5 if runnerish else 0
    score+=5 if historical_input else 0
    score-=25*len(dangerous)
    if "test_" in p.name.lower() or "/tests/" in rel.lower():score-=15

    return {
        "path":rel,
        "score":score,
        "hits":hits,
        "writes_target_report":writes_target,
        "producer_field_count":producer_fields,
        "runnerish":runnerish,
        "historical_input_markers":historical_input,
        "danger_markers":dangerous,
        "parse_ok":parse_ok,
        "functions":functions[:100],
        "classes":classes[:50],
        "imports":imports[:50],
        "cli_flags":sorted(set(re.findall(r'--[A-Za-z0-9_-]+',txt)))[:100],
    }

def inspect_ps(p:Path,root:Path):
    rel=str(p.relative_to(root)).replace("\\","/")
    txt=text(p)
    if not txt:return None
    hits=[t for t in TERMS if t.lower() in txt.lower()]
    if not hits:return None
    calls=re.findall(r'(?:python|python\.exe|\.\\\.venv\\scripts\\python\.exe)\s+([^\r\n]+)',txt,re.I)
    return {"path":rel,"hits":hits,"python_calls":calls[:50]}

def load_current_report(root:Path):
    p=root/"release/v11001_12000_multi_timeframe_ai/actual/multi_timeframe_ai_report_bilingual.json"
    result={"exists":p.exists(),"path":str(p.relative_to(root)).replace("\\","/")}
    if not p.exists():
        return result
    try:
        doc=json.loads(p.read_text(encoding="utf-8-sig"))
        analyses=doc.get("analyses",[]) if isinstance(doc,dict) else []
        result.update({
            "analysis_count":len(analyses) if isinstance(analyses,list) else 0,
            "symbols":[str(x.get("symbol","")).upper() for x in analyses if isinstance(x,dict)],
            "actions":[str(x.get("action","")).upper() for x in analyses if isinstance(x,dict)],
            "has_confidence_calibration":any(isinstance(x,dict) and "confidence_calibration" in x for x in analyses),
            "has_reward_risk":any(isinstance(x,dict) and "reward_risk" in x for x in analyses),
            "has_consensus_score":any(isinstance(x,dict) and "consensus_score" in x for x in analyses),
            "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
        })
    except Exception as e:
        result["parse_error"]=f"{type(e).__name__}: {e}"
    return result

def current_selector_contract(root:Path):
    p=root/"paper_autonomous_execution/signals.py"
    txt=text(p)
    return {
        "path":"paper_autonomous_execution/signals.py",
        "exists":p.exists(),
        "select_candidate_present":"def select_candidate" in txt,
        "allowed_symbols_filter":"symbol in allowed_symbols" in txt,
        "buy_sell_filter":'action in {"BUY", "SELL"}' in txt,
        "confidence_filter":"confidence >= min_confidence" in txt,
        "reward_risk_filter":"reward_risk >= min_reward_risk" in txt,
        "analysis_only_guard":'execution_mode") == "ANALYSIS_ONLY"' in txt,
        "sort_confidence_reward_risk":"eligible.sort" in txt and "reverse=True" in txt,
    }

def build(root:Path):
    root=Path(root).resolve()
    py=[];ps=[]
    for p in root.rglob("*"):
        if not p.is_file() or skip(p,root):continue
        if p.suffix.lower()==".py":
            x=inspect_python(p,root)
            if x:py.append(x)
        elif p.suffix.lower()==".ps1":
            x=inspect_ps(p,root)
            if x:ps.append(x)

    py.sort(key=lambda x:(x["score"],x["path"]),reverse=True)
    producers=[x for x in py if x["writes_target_report"] or x["producer_field_count"]>=3]
    safe_producers=[x for x in producers if not x["danger_markers"]]
    replay_capable=[
        x for x in safe_producers
        if x["historical_input_markers"] and (x["runnerish"] or x["functions"])
    ]

    report_state=load_current_report(root)
    selector=current_selector_contract(root)

    if replay_capable:
        state="CANONICAL_PRODUCER_CANDIDATE_FOUND_REVIEW_REQUIRED"
    elif safe_producers:
        state="PRODUCER_FOUND_BUT_HISTORICAL_ADAPTER_REQUIRED"
    else:
        state="CANONICAL_PRODUCER_NOT_YET_IDENTIFIED"

    out=root/"runtime/paper_strategy_lineage"
    out.mkdir(parents=True,exist_ok=True)
    report={
        "stage":"PAPER_STRATEGY_LINEAGE_HISTORICAL_REPLAY_FEASIBILITY_V1",
        "status":"PASS",
        "mode":"STATIC_READ_ONLY_LINEAGE_AUDIT",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "current_signal_report":report_state,
        "current_selector_contract":selector,
        "python_reference_count":len(py),
        "powershell_reference_count":len(ps),
        "producer_candidate_count":len(producers),
        "safe_producer_candidate_count":len(safe_producers),
        "historical_replay_capable_candidate_count":len(replay_capable),
        "top_producer_candidates":safe_producers[:20],
        "historical_replay_candidates":replay_capable[:20],
        "powershell_reference_map":ps[:50],
        "replay_feasibility_state":state,
        "required_equivalence_contract":{
            "must_generate_same_analyses_schema":True,
            "must_use_same_confidence_calibration":True,
            "must_use_same_reward_risk_logic":True,
            "must_use_same_consensus_score_logic":True,
            "must_reuse_current_select_candidate":True,
            "must_not_modify_current_paper_files":True,
            "must_not_submit_orders":True,
        },
        "contracts":{
            "paper_task_modified":False,
            "current_signal_report_modified":False,
            "candidate_producer_executed":False,
            "historical_replay_executed":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "strategy_parameter_changed":False,
            "new_strategy_created":False,
            "live_auto_enable":False,
        },
    }
    (out/"latest_paper_strategy_lineage.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    print(json.dumps(build(Path(a.root)),indent=2,default=str))
