from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse, hashlib, json, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow

PRIMARY_DATA_REL="runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl"
OUT_DIR_REL="runtime/regime_aware_buy_shadow_v2_7"
CANDIDATES={
    "MSFT_ONLY_30M":{
        "symbols":{"MSFT"},
        "dedup_minutes":15,
        "horizon_minutes":30,
        "cost_bps":5,
    },
    "MSFT_NVDA_30M":{
        "symbols":{"MSFT","NVDA"},
        "dedup_minutes":15,
        "horizon_minutes":30,
        "cost_bps":5,
    },
}


def sha256_file(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(path:Path):
    by=defaultdict(list)
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        if not line.strip():
            continue
        r=json.loads(line)
        sym=str(r.get("symbol","")).upper()
        if sym:
            by[sym].append(r)
    for sym in by:
        by[sym].sort(key=lambda x:x["timestamp"])
    return dict(by)


def latest_checkpoint(by):
    cps=shadow.make_checkpoints(by)
    if not cps:
        return None
    return cps[-1]


def classify_1d(item):
    one=next((x for x in item.get("timeframes",[]) if x.get("timeframe")=="1d"),None)
    if not one:
        return "MISSING"
    return str(one.get("signal","HOLD")).upper()


def ledger_read(path:Path):
    if not path.exists():
        return []
    rows=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        if line.strip():
            try: rows.append(json.loads(line))
            except Exception: pass
    return rows


def append_jsonl(path:Path,row):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,default=str)+"\n")


def candidate_allowed(name,item,cp,history):
    cfg=CANDIDATES[name]
    sym=str(item.get("symbol","")).upper()
    if sym not in cfg["symbols"]:
        return False,"SYMBOL_NOT_IN_CANDIDATE"
    if str(item.get("action","HOLD")).upper()!="BUY":
        return False,"NOT_BUY_ACTION"
    if classify_1d(item)!="SELL":
        return False,"ONE_DAY_NOT_OPPOSITE_SELL"

    last=[
        r for r in history
        if r.get("candidate")==name
        and r.get("symbol")==sym
        and r.get("event_type")=="SHADOW_SIGNAL"
    ]
    if last:
        try:
            prev=datetime.fromisoformat(last[-1]["checkpoint_et"])
            if (cp-prev).total_seconds() < cfg["dedup_minutes"]*60:
                return False,"DEDUP_WINDOW"
        except Exception:
            pass
    return True,"PASS"


def finalize_due_outcomes(by,ledger_path:Path,now_cp):
    history=ledger_read(ledger_path)
    existing={r.get("signal_id") for r in history if r.get("event_type")=="SHADOW_OUTCOME"}
    emitted=[]
    for r in history:
        if r.get("event_type")!="SHADOW_SIGNAL":
            continue
        sid=r.get("signal_id")
        if not sid or sid in existing:
            continue
        signal_cp=datetime.fromisoformat(r["checkpoint_et"])
        horizon=int(r.get("horizon_minutes",30))
        if now_cp < signal_cp+timedelta(minutes=horizon):
            continue
        sym=r["symbol"]
        rows=by.get(sym,[])
        future=[]
        for bar in rows:
            t=shadow.parse_timestamp(bar["timestamp"]).astimezone(shadow.ET)
            if signal_cp < t <= signal_cp+timedelta(minutes=horizon):
                future.append((t,bar))
        if not future:
            continue
        entry=float(future[0][1]["open"])
        exit_price=float(future[-1][1]["close"])
        gross=(exit_price-entry)/entry
        cost=float(r.get("cost_bps",5))/10000.0
        outcome={
            "event_type":"SHADOW_OUTCOME",
            "signal_id":sid,
            "candidate":r["candidate"],
            "symbol":sym,
            "checkpoint_et":r["checkpoint_et"],
            "resolved_at_checkpoint_et":now_cp.isoformat(),
            "entry_price":entry,
            "exit_price":exit_price,
            "gross_return":gross,
            "net_return_after_cost":gross-cost,
            "cost_bps":r.get("cost_bps",5),
            "paper_order_submitted":False,
            "live_order_submitted":False,
        }
        append_jsonl(ledger_path,outcome)
        emitted.append(outcome)
    return emitted


def run_once(root:Path):
    root=root.resolve()
    data_path=root/PRIMARY_DATA_REL
    if not data_path.exists():
        raise RuntimeError(f"Primary market-data dataset missing: {data_path}")

    by=load_rows(data_path)
    cp=latest_checkpoint(by)
    if cp is None:
        raise RuntimeError("No canonical checkpoint available")

    truncated=shadow.truncate_by_checkpoint(by,cp)
    analyses,feature_audit,rejected,production_selected=shadow.analyze_at_rows(truncated)

    out=root/OUT_DIR_REL
    out.mkdir(parents=True,exist_ok=True)
    ledger=out/"shadow_candidate_ledger.jsonl"
    history=ledger_read(ledger)

    outcomes=finalize_due_outcomes(by,ledger,cp)
    history=ledger_read(ledger)

    signals=[]
    for name in CANDIDATES:
        for item in analyses:
            ok,reason=candidate_allowed(name,item,cp,history)
            if not ok:
                continue
            sym=str(item.get("symbol","")).upper()
            sid=f"{name}|{sym}|{cp.isoformat()}"
            if any(r.get("signal_id")==sid for r in history):
                continue
            cfg=CANDIDATES[name]
            row={
                "event_type":"SHADOW_SIGNAL",
                "signal_id":sid,
                "generated_at_utc":datetime.now(timezone.utc).isoformat(),
                "candidate":name,
                "symbol":sym,
                "checkpoint_et":cp.isoformat(),
                "horizon_minutes":cfg["horizon_minutes"],
                "cost_bps":cfg["cost_bps"],
                "canonical_action":item.get("action"),
                "one_day_signal":"SELL",
                "consensus_score":item.get("consensus_score"),
                "reward_risk":item.get("reward_risk"),
                "calibrated_confidence":item.get("confidence_calibration",{}).get("calibrated_confidence"),
                "production_selected_candidate":production_selected,
                "paper_order_submitted":False,
                "live_order_submitted":False,
                "broker_write_performed":False,
            }
            append_jsonl(ledger,row)
            signals.append(row)
            history.append(row)

    snapshot={
        "stage":"V2.7_REALTIME_SHADOW_CANDIDATE_STRATEGY",
        "status":"PASS",
        "mode":"READ_ONLY_SHADOW",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "checkpoint_et":cp.isoformat(),
        "source_dataset":PRIMARY_DATA_REL,
        "source_dataset_sha256":sha256_file(data_path),
        "analysis_count":len(analyses),
        "rejected_symbols":rejected,
        "feature_audit":feature_audit,
        "production_selected_candidate_observed_only":production_selected,
        "new_shadow_signals":signals,
        "new_shadow_outcomes":outcomes,
        "candidate_definitions":{
            k:{**v,"symbols":sorted(v["symbols"])} for k,v in CANDIDATES.items()
        },
        "contracts":{
            "paper_runtime_modified":False,
            "production_parameter_modified":False,
            "production_selector_modified":False,
            "broker_trading_client_created":False,
            "broker_write_performed":False,
            "paper_order_submission_performed":False,
            "live_order_submission_performed":False,
            "automatic_promotion":False,
            "network_used_by_v2_7":False,
        },
    }
    (out/"latest_shadow_snapshot.json").write_text(
        json.dumps(snapshot,indent=2,default=str),encoding="utf-8"
    )
    print(json.dumps(snapshot,indent=2,default=str))
    return snapshot


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    run_once(Path(a.root))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
