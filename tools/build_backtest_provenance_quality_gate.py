from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

TRUST_ORDER={
    "REAL_HISTORICAL_BACKTEST":5,
    "SIMULATED_BACKTEST":4,
    "PAPER_ACTUAL":3,
    "SYNTHETIC_SCENARIO":2,
    "FIXTURE":1,
    "EXAMPLE":0,
    "UNKNOWN":0,
}

def read_jsonl(path:Path):
    rows=[]
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            x=json.loads(line)
            if isinstance(x,dict):
                rows.append(x)
        except Exception:
            pass
    return rows

def classify_source(source:str):
    s=(source or "").replace("\\","/").lower()

    if "/fixture" in s or "fixture." in s or "/fixtures/" in s:
        return "FIXTURE"
    if "example" in s:
        return "EXAMPLE"
    if "paper_trade_scenarios" in s or "/scenarios/" in s:
        return "SYNTHETIC_SCENARIO"
    if "paper_exit_ledger" in s or "actual/" in s and "paper" in s:
        return "PAPER_ACTUAL"

    # Explicit historical/backtest engine output families.
    hist_markers=(
        "historical_backtest",
        "backtest_v2",
        "multi_asset_backtest",
        "offline_candidate_backtest",
        "walk_forward",
        "oos",
        "historical_portfolio_simulation",
        "historical_performance",
    )
    if any(m in s for m in hist_markers):
        return "REAL_HISTORICAL_BACKTEST"

    # General backtest outputs that are not obvious fixtures/scenarios.
    if "backtest" in s:
        return "SIMULATED_BACKTEST"

    return "UNKNOWN"

def quality_flags(row:dict):
    flags=[]
    if not row.get("symbol"):
        flags.append("MISSING_SYMBOL")
    if row.get("realized_pl") is None:
        flags.append("MISSING_REALIZED_PL")
    if not row.get("entry_time"):
        flags.append("MISSING_ENTRY_TIME")
    if not row.get("exit_time"):
        flags.append("MISSING_EXIT_TIME")
    return flags

def identity_key(row:dict):
    payload={
        "symbol":row.get("symbol"),
        "realized_pl":row.get("realized_pl"),
        "entry_time":row.get("entry_time"),
        "exit_time":row.get("exit_time"),
        "side":row.get("side"),
        "exit_reason":row.get("exit_reason"),
        "source":row.get("_canonical_source"),
    }
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()

def build(root:Path):
    root=Path(root).resolve()
    src=root/"runtime/canonical_backtest_feed/canonical_backtest_trades.jsonl"
    rows=read_jsonl(src)

    classified=[]
    counts={}
    usable=[]
    excluded=[]
    seen=set()

    for r in rows:
        x=dict(r)
        source=str(x.get("_canonical_source") or "")
        cls=classify_source(source)
        flags=quality_flags(x)
        trust=TRUST_ORDER.get(cls,0)

        # Duplicate at provenance level.
        ident=identity_key(x)
        if ident in seen:
            flags.append("DUPLICATE_PROVENANCE_RECORD")
        else:
            seen.add(ident)

        x["_provenance_class"]=cls
        x["_provenance_trust_score"]=trust
        x["_quality_flags"]=flags
        x["_quality_pass"]=len(flags)==0

        counts[cls]=counts.get(cls,0)+1
        classified.append(x)

        # Curated feed policy:
        # Only historical/backtest-like records, complete enough for comparison.
        if cls in {"REAL_HISTORICAL_BACKTEST","SIMULATED_BACKTEST"} and len(flags)==0:
            usable.append(x)
        else:
            excluded.append(x)

    out=root/"runtime/backtest_provenance_quality_gate"
    out.mkdir(parents=True,exist_ok=True)

    def write_jsonl(path,items):
        with path.open("w",encoding="utf-8") as h:
            for r in items:
                h.write(json.dumps(r,default=str)+"\n")

    write_jsonl(out/"classified_backtest_records.jsonl",classified)
    write_jsonl(out/"curated_cross_validation_feed.jsonl",usable)
    write_jsonl(out/"excluded_records.jsonl",excluded)

    report={
        "stage":"BACKTEST_PROVENANCE_QUALITY_GATE_V1",
        "status":"PASS",
        "mode":"RESEARCH_ONLY_DERIVED_DATA",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_feed":"runtime/canonical_backtest_feed/canonical_backtest_trades.jsonl",
        "input_record_count":len(rows),
        "provenance_counts":counts,
        "curated_record_count":len(usable),
        "excluded_record_count":len(excluded),
        "curated_feed_path":"runtime/backtest_provenance_quality_gate/curated_cross_validation_feed.jsonl",
        "excluded_feed_path":"runtime/backtest_provenance_quality_gate/excluded_records.jsonl",
        "quality_policy":{
            "allowed_classes":["REAL_HISTORICAL_BACKTEST","SIMULATED_BACKTEST"],
            "required_fields":["symbol","realized_pl","entry_time","exit_time"],
            "synthetic_scenarios_allowed":False,
            "fixtures_allowed":False,
            "examples_allowed":False,
            "paper_actual_allowed_in_backtest_feed":False,
        },
        "next_state":"CURATED_FEED_READY" if usable else "NEEDS_HISTORICAL_REPLAY_GENERATION",
        "contracts":{
            "source_feed_modified":False,
            "paper_task_modified":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "strategy_parameter_changed":False,
            "risk_parameter_changed":False,
            "new_backtest_engine_created":False,
            "new_strategy_created":False,
            "live_auto_enable":False,
        },
    }
    (out/"latest_provenance_quality_report.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    args=p.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
