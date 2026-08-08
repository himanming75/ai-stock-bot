from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict, Counter
from datetime import timedelta, datetime, timezone
from pathlib import Path
import argparse, json, statistics, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow

TARGET_START="2026-06-15"
TARGET_END="2026-07-07"
RECOVERY_REL="runtime/v1_7_3_holdout_recovery/alpaca_real_historical_holdout_75d.jsonl"

SYMBOL_GROUPS={
    "ALL":["AAPL","MSFT","NVDA","SPY"],
    "MSFT_NVDA":["MSFT","NVDA"],
    "MSFT_ONLY":["MSFT"],
    "NVDA_ONLY":["NVDA"],
    "AAPL_ONLY":["AAPL"],
}
HORIZONS=(30,45)
ROUND_TRIP_COSTS_BPS=(0,2,5,10)
DEDUP_MINUTES=(0,15,30,45)
TP_PCT=0.015
SL_PCT=0.0075
MAX_HOLD_MINUTES=45


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
    return {
        sym:(
            [shadow.parse_timestamp(r["timestamp"]).astimezone(shadow.ET) for r in rows],
            rows
        )
        for sym,rows in by.items()
    }


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
    if sig=="SELL":
        return "1D_OPPOSITE_SELL"
    if sig=="BUY":
        return "1D_ALIGNED_BUY"
    return "1D_HOLD"


def dedup(rows, minutes):
    if minutes<=0:
        return list(rows)
    kept=[]
    last_by_symbol={}
    for r in sorted(rows,key=lambda x:x["checkpoint_dt"]):
        sym=r["symbol"]
        prev=last_by_symbol.get(sym)
        if prev is None or (r["checkpoint_dt"]-prev).total_seconds()>=minutes*60:
            kept.append(r)
            last_by_symbol[sym]=r["checkpoint_dt"]
    return kept


def fixed_horizon_return(index,symbol,cp,horizon):
    times,rows=index[symbol]
    start=bisect_right(times,cp)
    if start>=len(rows):
        return None
    entry=float(rows[start]["open"])
    entry_time=times[start]
    end=bisect_right(times,entry_time+timedelta(minutes=horizon))-1
    if end<start:
        return None
    exit_price=float(rows[end]["close"])
    return (exit_price-entry)/entry


def lifecycle_return(index,symbol,cp):
    times,rows=index[symbol]
    start=bisect_right(times,cp)
    if start>=len(rows):
        return None
    entry_time=times[start]
    entry=float(rows[start]["open"])
    tp=entry*(1+TP_PCT)
    sl=entry*(1-SL_PCT)
    end=bisect_right(times,entry_time+timedelta(minutes=MAX_HOLD_MINUTES))-1
    if end<start:
        return None

    exit_reason="TIME"
    exit_price=float(rows[end]["close"])
    for i in range(start,end+1):
        low=float(rows[i]["low"])
        high=float(rows[i]["high"])
        # conservative ambiguity
        if low<=sl:
            exit_reason="SL"
            exit_price=sl
            break
        if high>=tp:
            exit_reason="TP"
            exit_price=tp
            break
    return {
        "gross_return":(exit_price-entry)/entry,
        "exit_reason":exit_reason,
    }


def summarize(vals):
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

    base_rows=[]
    for i,cp in enumerate(checkpoints,1):
        analyses,_,rejected,_=shadow.analyze_at_rows(trunc(index,cp))
        if rejected or len(analyses)!=len(shadow.ALLOWED):
            continue

        for item in analyses:
            if str(item.get("action","HOLD")).upper()!="BUY":
                continue
            if classify_1d(item)!="1D_OPPOSITE_SELL":
                continue

            sym=str(item.get("symbol","")).upper()
            rec={
                "checkpoint_et":cp.isoformat(),
                "checkpoint_dt":cp,
                "date":cp.date().isoformat(),
                "symbol":sym,
                "confidence":float(item.get("confidence_calibration",{}).get("calibrated_confidence",0.0)),
                "reward_risk":float(item.get("reward_risk",0.0)),
                "consensus_score":float(item.get("consensus_score",0.0)),
                "horizon_returns":{},
                "lifecycle":lifecycle_return(index,sym,cp),
            }
            for h in HORIZONS:
                rec["horizon_returns"][str(h)]=fixed_horizon_return(index,sym,cp,h)
            base_rows.append(rec)

        if i%25==0 or i==len(checkpoints):
            print(f"V2.5 REGIME COUNTERFACTUAL PROGRESS: {i}/{len(checkpoints)}",flush=True)

    if not base_rows:
        raise RuntimeError("No 1D-opposite BUY rows")

    matrix={}
    for group_name,symbols in SYMBOL_GROUPS.items():
        group_rows=[r for r in base_rows if r["symbol"] in symbols]
        matrix[group_name]={}
        for dedup_min in DEDUP_MINUTES:
            subset=dedup(group_rows,dedup_min)
            matrix[group_name][str(dedup_min)]={}
            for cost_bps in ROUND_TRIP_COSTS_BPS:
                cost=cost_bps/10000.0
                horizons={}
                for h in HORIZONS:
                    vals=[
                        r["horizon_returns"][str(h)]-cost
                        for r in subset
                        if r["horizon_returns"].get(str(h)) is not None
                    ]
                    horizons[str(h)]=summarize(vals)

                life_vals=[
                    r["lifecycle"]["gross_return"]-cost
                    for r in subset if r["lifecycle"] is not None
                ]
                exit_counts=Counter(
                    r["lifecycle"]["exit_reason"]
                    for r in subset if r["lifecycle"] is not None
                )
                matrix[group_name][str(dedup_min)][str(cost_bps)]={
                    "signal_count":len(subset),
                    "by_symbol":dict(Counter(r["symbol"] for r in subset)),
                    "fixed_horizon":horizons,
                    "lifecycle_45m_tp15_sl075":{
                        **summarize(life_vals),
                        "exit_counts":dict(exit_counts),
                    },
                }

    # Candidate selection: diagnostic only. Require positive mean after 5bps,
    # positive median, win-rate > 50%, at least 15 deduped observations.
    candidates=[]
    for group_name in SYMBOL_GROUPS:
        for dedup_min in (15,30,45):
            cell=matrix[group_name][str(dedup_min)]["5"]
            for horizon in ("30","45"):
                s=cell["fixed_horizon"][horizon]
                if (
                    s["count"]>=15
                    and s["mean"] is not None and s["mean"]>0
                    and s["median"] is not None and s["median"]>0
                    and s["win_rate"] is not None and s["win_rate"]>0.50
                ):
                    candidates.append({
                        "group":group_name,
                        "dedup_minutes":dedup_min,
                        "cost_bps":5,
                        "horizon_minutes":int(horizon),
                        **s,
                    })

    candidates.sort(
        key=lambda x:(x["mean"],x["win_rate"],x["count"]),
        reverse=True
    )

    report={
        "stage":"V2.5_REGIME_AWARE_BUY_COUNTERFACTUAL_AND_NET_COST_LIFECYCLE_AUDIT",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "baseline_signal_count":len(base_rows),
        "scenario_matrix":matrix,
        "diagnostic_candidate_rules":{
            "minimum_observations":15,
            "stress_cost_bps":5,
            "requires_positive_mean":True,
            "requires_positive_median":True,
            "requires_win_rate_gt_50pct":True,
            "automatic_promotion":False,
        },
        "surviving_diagnostic_candidates":candidates,
        "top_diagnostic_candidate":candidates[0] if candidates else None,
        "interpretation_contract":{
            "counterfactual_only":True,
            "regime_rule_applied_to_production":False,
            "symbol_filter_applied_to_production":False,
            "dedup_rule_applied_to_production":False,
            "cost_model_applied_to_production":False,
            "rr_threshold_changed":False,
            "one_day_weight_changed":False,
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
            for r in base_rows
        ],
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_regime_aware_buy_counterfactual_v2_5.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    compact={
        "stage":report["stage"],
        "status":report["status"],
        "baseline_signal_count":report["baseline_signal_count"],
        "top_diagnostic_candidate":report["top_diagnostic_candidate"],
        "surviving_diagnostic_candidate_count":len(candidates),
        "surviving_diagnostic_candidates":candidates[:20],
        "msft_nvda_45m_5bps":matrix["MSFT_NVDA"]["45"]["5"],
        "all_45m_5bps":matrix["ALL"]["45"]["5"],
        "contracts":report["contracts"],
    }
    print(json.dumps(compact,indent=2,default=str))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    build(Path(a.root))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
