from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse, json, sys, statistics

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow

TARGET_START="2026-06-15"
TARGET_END="2026-07-07"
RECOVERY_REL="runtime/v1_7_3_holdout_recovery/alpaca_real_historical_holdout_75d.jsonl"

HORIZONS=(5,15,30,45)
ENTRY_DELAYS=(0,1,3,5)
ROUND_TRIP_COSTS_BPS=(0,2,5,10,20)
DEDUP_WINDOWS_MIN=(0,5,15,30,45)


def load_recovery(root:Path):
    p=root/RECOVERY_REL
    if not p.exists():
        raise RuntimeError(f"Recovered source missing: {p}")
    by=defaultdict(list)
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r=json.loads(line)
            by[str(r["symbol"]).upper()].append(r)
    for sym in by:
        by[sym].sort(key=lambda x:x["timestamp"])
    return dict(by)


def build_index(by):
    out={}
    for sym,rows in by.items():
        times=[shadow.parse_timestamp(r["timestamp"]).astimezone(shadow.ET) for r in rows]
        out[sym]=(times,rows)
    return out


def trunc(index,cp):
    return {
        sym: rows[:bisect_right(times,cp)]
        for sym,(times,rows) in index.items()
    }


def classify_1d(item):
    one=next((x for x in item.get("timeframes",[]) if x.get("timeframe")=="1d"),None)
    if not one:
        return "MISSING"
    sig=str(one.get("signal","HOLD")).upper()
    if sig=="BUY": return "1D_ALIGNED_BUY"
    if sig=="SELL": return "1D_OPPOSITE_SELL"
    return "1D_HOLD"


def get_price_after(index,symbol,cp,delay_min,horizon_min):
    times,rows=index[symbol]
    entry_target=cp+timedelta(minutes=delay_min)
    start=bisect_right(times,entry_target)
    if start>=len(rows):
        return None
    entry_time=times[start]
    entry=float(rows[start]["open"])

    exit_target=entry_time+timedelta(minutes=horizon_min)
    end=bisect_right(times,exit_target)-1
    if end<start:
        return None
    exit_time=times[end]
    exit_price=float(rows[end]["close"])

    highs=[float(rows[i]["high"]) for i in range(start,end+1)]
    lows=[float(rows[i]["low"]) for i in range(start,end+1)]
    return {
        "entry_time_et":entry_time.isoformat(),
        "exit_time_et":exit_time.isoformat(),
        "entry_price":entry,
        "exit_price":exit_price,
        "gross_return":(exit_price-entry)/entry,
        "mfe":(max(highs)-entry)/entry,
        "mae":(min(lows)-entry)/entry,
        "bar_count":end-start+1,
    }


def dedup(rows,window_min):
    if window_min<=0:
        return list(rows)
    kept=[]
    last_by_symbol={}
    for r in sorted(rows,key=lambda x:x["checkpoint_dt"]):
        sym=r["symbol"]
        prev=last_by_symbol.get(sym)
        if prev is None or (r["checkpoint_dt"]-prev).total_seconds()>=window_min*60:
            kept.append(r)
            last_by_symbol[sym]=r["checkpoint_dt"]
    return kept


def summarize_returns(vals):
    if not vals:
        return {"count":0,"mean":None,"median":None,"win_rate":None,"sum":None}
    return {
        "count":len(vals),
        "mean":statistics.mean(vals),
        "median":statistics.median(vals),
        "win_rate":sum(1 for x in vals if x>0)/len(vals),
        "sum":sum(vals),
    }


def build(root:Path):
    root=Path(root).resolve()
    by=load_recovery(root)
    index=build_index(by)
    dates=sorted(shadow.regular_session_rows(by.get("SPY",[])).keys())
    wanted={d for d in dates if TARGET_START<=d<=TARGET_END}
    checkpoints=[cp for cp in shadow.make_checkpoints(by) if cp.date().isoformat() in wanted]

    rows=[]
    for i,cp in enumerate(checkpoints,1):
        analyses,_,rejected,_=shadow.analyze_at_rows(trunc(index,cp))
        if rejected or len(analyses)!=len(shadow.ALLOWED):
            continue
        for item in analyses:
            if str(item.get("action","HOLD")).upper()!="BUY":
                continue
            if classify_1d(item)!="1D_OPPOSITE_SELL":
                continue
            symbol=str(item.get("symbol","")).upper()
            one=next((x for x in item.get("timeframes",[]) if x.get("timeframe")=="1d"),{})
            rec={
                "checkpoint_et":cp.isoformat(),
                "checkpoint_dt":cp,
                "date":cp.date().isoformat(),
                "symbol":symbol,
                "consensus_score":float(item.get("consensus_score",0.0)),
                "reward_risk":float(item.get("reward_risk",0.0)),
                "calibrated_confidence":float(item.get("confidence_calibration",{}).get("calibrated_confidence",0.0)),
                "one_day_directional_score":float(one.get("directional_score",0.0)),
            }
            rec["outcomes"]={}
            for delay in ENTRY_DELAYS:
                rec["outcomes"][str(delay)]={}
                for horizon in HORIZONS:
                    o=get_price_after(index,symbol,cp,delay,horizon)
                    if o:
                        rec["outcomes"][str(delay)][str(horizon)]=o
            rows.append(rec)
        if i%25==0 or i==len(checkpoints):
            print(f"V2.4 ROBUSTNESS PROGRESS: {i}/{len(checkpoints)}",flush=True)

    if not rows:
        raise RuntimeError("No 1D-opposite BUY rows found")

    dedup_results={}
    for window in DEDUP_WINDOWS_MIN:
        subset=dedup(rows,window)
        horizon_summary={}
        for horizon in HORIZONS:
            vals=[]
            for r in subset:
                o=r["outcomes"].get("0",{}).get(str(horizon))
                if o: vals.append(o["gross_return"])
            horizon_summary[str(horizon)]=summarize_returns(vals)
        dedup_results[str(window)]={
            "count":len(subset),
            "by_symbol":dict(Counter(r["symbol"] for r in subset)),
            "by_date":dict(Counter(r["date"] for r in subset)),
            "horizons":horizon_summary,
        }

    delay_results={}
    for delay in ENTRY_DELAYS:
        hs={}
        for horizon in HORIZONS:
            vals=[]
            for r in rows:
                o=r["outcomes"].get(str(delay),{}).get(str(horizon))
                if o: vals.append(o["gross_return"])
            hs[str(horizon)]=summarize_returns(vals)
        delay_results[str(delay)]={"horizons":hs}

    cost_results={}
    base45=[]
    for r in rows:
        o=r["outcomes"].get("0",{}).get("45")
        if o: base45.append(o["gross_return"])
    for bps in ROUND_TRIP_COSTS_BPS:
        cost=bps/10000.0
        net=[x-cost for x in base45]
        cost_results[str(bps)]=summarize_returns(net)

    by_symbol={}
    for sym in sorted({r["symbol"] for r in rows}):
        subset=[r for r in rows if r["symbol"]==sym]
        vals=[]
        for r in subset:
            o=r["outcomes"].get("0",{}).get("45")
            if o: vals.append(o["gross_return"])
        by_symbol[sym]=summarize_returns(vals)

    by_date={}
    for day in sorted({r["date"] for r in rows}):
        subset=[r for r in rows if r["date"]==day]
        vals=[]
        for r in subset:
            o=r["outcomes"].get("0",{}).get("45")
            if o: vals.append(o["gross_return"])
        by_date[day]=summarize_returns(vals)

    mfe_vals=[]
    mae_vals=[]
    for r in rows:
        o=r["outcomes"].get("0",{}).get("45")
        if o:
            mfe_vals.append(o["mfe"]); mae_vals.append(o["mae"])

    report={
        "stage":"V2.4_1D_OPPOSITE_BUY_ROBUSTNESS_COST_TIMING_DEDUP_AUDIT",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "sample":{"raw_signal_count":len(rows)},
        "deduplication_stress":dedup_results,
        "entry_delay_stress":delay_results,
        "round_trip_cost_stress_bps_on_45m":cost_results,
        "symbol_breakdown_45m":by_symbol,
        "date_breakdown_45m":by_date,
        "path_excursions_45m":{
            "mfe_mean":statistics.mean(mfe_vals) if mfe_vals else None,
            "mfe_median":statistics.median(mfe_vals) if mfe_vals else None,
            "mae_mean":statistics.mean(mae_vals) if mae_vals else None,
            "mae_median":statistics.median(mae_vals) if mae_vals else None,
        },
        "interpretation_contract":{
            "diagnostic_only":True,
            "production_entry_rule_changed":False,
            "cost_model_applied_to_production":False,
            "dedup_rule_applied_to_production":False,
            "one_day_weight_changed":False,
            "rr_threshold_changed":False,
            "production_change_applied":False,
        },
        "contracts":{
            "paper_runtime_modified":False,
            "production_parameter_modified":False,
            "strategy_parameter_modified":False,
            "risk_parameter_modified":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "network_used":False,
            "duplicate_trading_engine_created":False,
            "automatic_promotion":False,
        },
        "rows":[
            {k:v for k,v in r.items() if k!="checkpoint_dt"}
            for r in rows
        ],
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_1d_opposite_buy_robustness_v2_4.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    print(json.dumps({
        "stage":report["stage"],
        "status":report["status"],
        "sample":report["sample"],
        "deduplication_stress":report["deduplication_stress"],
        "entry_delay_stress":report["entry_delay_stress"],
        "round_trip_cost_stress_bps_on_45m":report["round_trip_cost_stress_bps_on_45m"],
        "symbol_breakdown_45m":report["symbol_breakdown_45m"],
        "path_excursions_45m":report["path_excursions_45m"],
        "contracts":report["contracts"],
    },indent=2,default=str))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    build(Path(a.root))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
