from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse, json, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow

TARGET_START="2026-06-09"
TARGET_END="2026-07-07"
RECOVERY_REL="runtime/v1_7_3_holdout_recovery/alpaca_real_historical_holdout_75d.jsonl"


def load_recovery(root:Path):
    p=root/RECOVERY_REL
    if not p.exists():
        raise RuntimeError(f"Recovered V1.7.3 source missing: {p}")
    by=defaultdict(list)
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        by[str(r["symbol"]).upper()].append(r)
    for sym in by:
        by[sym].sort(key=lambda x:x["timestamp"])
    return dict(by)


def build_fast_index(by):
    return {
        sym:([shadow.parse_timestamp(r["timestamp"]).astimezone(shadow.ET) for r in rows],rows)
        for sym,rows in by.items()
    }


def fast_truncate(index,checkpoint):
    out={}
    for sym,(times,rows) in index.items():
        n=bisect_right(times,checkpoint)
        out[sym]=rows[:n]
    return out


def analysis_row(item):
    action=str(item.get("action","HOLD")).upper()
    conf=float(item.get("confidence_calibration",{}).get("calibrated_confidence",0.0))
    rr=float(item.get("reward_risk",0.0))
    return {
        "symbol":str(item.get("symbol","")).upper(),
        "action":action,
        "confidence":conf,
        "reward_risk":rr,
        "confidence_pass":conf>=shadow.MIN_CONFIDENCE,
        "reward_risk_pass":rr>=shadow.MIN_REWARD_RISK,
        "guardrail_pass":item.get("execution_mode")=="ANALYSIS_ONLY",
        "directional":action in {"BUY","SELL"},
    }


def classify(analyses,rejected,selected):
    rows=[analysis_row(x) for x in analyses]
    actions=Counter(x["action"] for x in rows)
    if rejected: cause="DATA_OR_FEATURE_COVERAGE"
    elif selected: cause="SELL_SELECTED_NO_LONG_ENTRY" if str(selected.get("side","")).upper()=="SELL" else "BUY_SELECTED"
    elif rows and actions.get("HOLD",0)==len(rows): cause="HOLD_ONLY"
    elif any(x["directional"] and not x["confidence_pass"] for x in rows): cause="CONFIDENCE_FILTER"
    elif any(x["directional"] and x["confidence_pass"] and not x["reward_risk_pass"] for x in rows): cause="REWARD_RISK_FILTER"
    else: cause="NO_ELIGIBLE_DIRECTIONAL_SIGNAL"
    return cause,rows


def audit(root:Path):
    root=Path(root).resolve()
    by=load_recovery(root)
    index=build_fast_index(by)

    market_dates=sorted(shadow.regular_session_rows(by.get("SPY",[])).keys())
    target_dates=[d for d in market_dates if TARGET_START<=d<=TARGET_END]
    wanted=set(target_dates)
    if not target_dates:
        raise RuntimeError("Recovered source has no target dates")

    all_cp=shadow.make_checkpoints(by)
    checkpoints=[cp for cp in all_cp if cp.date().isoformat() in wanted]
    if not checkpoints:
        raise RuntimeError("Canonical make_checkpoints returned zero target checkpoints")

    # Cache canonical analyzer results once per target checkpoint.
    decision_cache={}
    for i,cp in enumerate(checkpoints,1):
        truncated=fast_truncate(index,cp)
        analyses,feature_audit,rejected,selected=shadow.analyze_at_rows(truncated)
        decision_cache[cp.isoformat()]=(analyses,feature_audit,rejected,selected)
        if i%25==0 or i==len(checkpoints):
            print(f"AUDIT ANALYSIS PROGRESS: {i}/{len(checkpoints)}",flush=True)

    # Reuse canonical rolling_lifecycle, but constrain its checkpoint builder to
    # the already-resolved target checkpoint set and reuse the cached decisions.
    original_loader=shadow.load_real_rows
    original_make=shadow.make_checkpoints
    original_truncate=shadow.truncate_by_checkpoint
    original_analyze=shadow.analyze_at_rows

    def cached_truncate(_by,cp):
        return fast_truncate(index,cp)

    def cached_analyze(truncated):
        # Canonical lifecycle invokes truncate then analyze for each cp.
        # Determine cp from latest SPY row and serve the exact canonical result.
        spy=truncated.get("SPY",[])
        if not spy:
            return original_analyze(truncated)
        cp=shadow.parse_timestamp(spy[-1]["timestamp"]).astimezone(shadow.ET)
        key=cp.replace(second=0,microsecond=0).isoformat()
        return decision_cache.get(key,original_analyze(truncated))

    shadow.load_real_rows=lambda _root:by
    shadow.make_checkpoints=lambda _by:list(checkpoints)
    shadow.truncate_by_checkpoint=cached_truncate
    shadow.analyze_at_rows=cached_analyze
    try:
        lifecycle=shadow.rolling_lifecycle(root)
    finally:
        shadow.load_real_rows=original_loader
        shadow.make_checkpoints=original_make
        shadow.truncate_by_checkpoint=original_truncate
        shadow.analyze_at_rows=original_analyze

    accepted_signal_times={
        str(t.get("entry_signal_time_et"))
        for t in lifecycle.get("closed_trades",[])
        if t.get("entry_signal_time_et")
    }

    records=[]
    daily=defaultdict(lambda:{
        "checkpoints":0,"feature_complete":0,"buy":0,"sell":0,"none":0,
        "accepted":0,"buy_gap":0,"causes":Counter()
    })

    for cp in checkpoints:
        analyses,feature_audit,rejected,selected=decision_cache[cp.isoformat()]
        cause,rows=classify(analyses,rejected,selected)
        side=None if selected is None else str(selected.get("side","")).upper()
        accepted=bool(side=="BUY" and cp.isoformat() in accepted_signal_times)
        day=cp.date().isoformat()
        d=daily[day]; d["checkpoints"]+=1; d["causes"][cause]+=1
        if len(analyses)==len(shadow.ALLOWED) and not rejected:d["feature_complete"]+=1
        if side=="BUY":
            d["buy"]+=1
            if accepted:d["accepted"]+=1
            else:d["buy_gap"]+=1
        elif side=="SELL":d["sell"]+=1
        else:d["none"]+=1
        records.append({
            "checkpoint_et":cp.isoformat(),"date":day,"primary_cause":cause,
            "selected_candidate":selected,"buy_accepted":accepted,
            "feature_audit":feature_audit,"rejected_symbols":rejected,
            "analysis_rows":rows,
        })

    zero_dates=[]; root_causes=Counter(); daily_rows=[]
    for day in target_dates:
        d=daily[day]; zero=d["accepted"]==0
        if zero:zero_dates.append(day)
        if d["feature_complete"]<d["checkpoints"]:primary="DATA_OR_FEATURE_COVERAGE"
        elif d["buy"]>0 and d["accepted"]==0:primary="BUY_SIGNAL_LIFECYCLE_ENTRY_GAP"
        elif d["buy"]==0 and d["sell"]>0:primary="SELL_ONLY_OR_SELL_DOMINANT"
        elif d["causes"].get("HOLD_ONLY",0)>0 and d["buy"]==0:primary="HOLD_DOMINANT"
        elif d["causes"].get("CONFIDENCE_FILTER",0)>0 and d["buy"]==0:primary="CONFIDENCE_FILTER"
        elif d["causes"].get("REWARD_RISK_FILTER",0)>0 and d["buy"]==0:primary="REWARD_RISK_FILTER"
        elif zero:primary="NO_ACCEPTED_BUY_OTHER"
        else:primary="TRADED"
        if zero:root_causes[primary]+=1
        daily_rows.append({
            "date":day,"zero_trade":zero,"primary_root_cause":primary,
            "market_checkpoints":d["checkpoints"],
            "feature_complete_checkpoints":d["feature_complete"],
            "selected_buy":d["buy"],"selected_sell":d["sell"],
            "selected_none":d["none"],"accepted_buy_entries":d["accepted"],
            "buy_selected_but_not_accepted":d["buy_gap"],
            "checkpoint_cause_counts":dict(d["causes"]),
        })

    report={
        "stage":"V1.7.4_FAST_HOLDOUT_ZERO_TRADE_ROOT_CAUSE_AUDIT",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "performance_repair":{
            "bisect_indexed_truncation":True,
            "checkpoint_analysis_cache":True,
            "lifecycle_target_checkpoint_scope_only":True,
            "canonical_engine_logic_modified":False,
        },
        "canonical_reuse":{
            "checkpoint_builder":"shadow.make_checkpoints",
            "feature_analyzer":"shadow.analyze_at_rows",
            "selector":"existing select_candidate via analyze_at_rows",
            "lifecycle":"shadow.rolling_lifecycle",
            "duplicate_engine_created":False,
        },
        "scope_summary":{
            "trading_dates":len(target_dates),
            "market_checkpoints":len(checkpoints),
            "zero_trade_dates":len(zero_dates),
            "zero_trade_date_list":zero_dates,
            "zero_trade_day_root_cause_counts":dict(root_causes),
        },
        "lifecycle_crosscheck":{
            "entry_summary":lifecycle.get("entry_summary",{}),
            "checkpoint_summary":lifecycle.get("checkpoint_summary",{}),
        },
        "daily_audit":daily_rows,
        "checkpoint_audit":records,
        "contracts":{
            "paper_runtime_modified":False,
            "production_parameter_modified":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "runtime_primary_dataset_modified":False,
            "network_used_by_audit":False,
            "automatic_promotion":False,
        },
    }
    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_holdout_zero_trade_audit_v1_7_4.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )
    print("AUDIT REPORT WRITTEN",flush=True)
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    r=audit(Path(a.root))
    print(json.dumps({
        "stage":r["stage"],
        "status":r["status"],
        "scope_summary":r["scope_summary"],
        "lifecycle_crosscheck":r["lifecycle_crosscheck"],
        "contracts":r["contracts"],
    },indent=2,default=str))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
