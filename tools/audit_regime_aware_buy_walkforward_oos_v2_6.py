from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict, Counter
from datetime import timedelta, datetime, timezone
from pathlib import Path
import argparse, json, statistics, sys, math

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow

TARGET_START="2026-06-15"
TARGET_END="2026-07-07"
RECOVERY_REL="runtime/v1_7_3_holdout_recovery/alpaca_real_historical_holdout_75d.jsonl"

FIXED_CANDIDATES={
    "MSFT_ONLY_30M":{
        "symbols":{"MSFT"},
        "dedup_minutes":15,
        "horizon_minutes":30,
    },
    "MSFT_NVDA_30M":{
        "symbols":{"MSFT","NVDA"},
        "dedup_minutes":15,
        "horizon_minutes":30,
    },
}
COST_BPS=(5,10)
WINDOW_TRADING_DAYS=5


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


def fixed_return(index,symbol,cp,horizon):
    times,rows=index[symbol]
    start=bisect_right(times,cp)
    if start>=len(rows):
        return None
    entry_time=times[start]
    entry=float(rows[start]["open"])
    end=bisect_right(times,entry_time+timedelta(minutes=horizon))-1
    if end<start:
        return None
    exit_price=float(rows[end]["close"])
    return (exit_price-entry)/entry


def dedup(rows,minutes):
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


def max_drawdown_simple(returns):
    eq=0.0
    peak=0.0
    mdd=0.0
    for r in returns:
        eq += r
        peak=max(peak,eq)
        mdd=min(mdd,eq-peak)
    return mdd


def chunk_dates(dates,n):
    return [dates[i:i+n] for i in range(0,len(dates),n) if dates[i:i+n]]


def build(root:Path):
    root=Path(root).resolve()
    by=load_recovery(root)
    index=build_index(by)

    trading_dates=sorted(
        d for d in shadow.regular_session_rows(by.get("SPY",[])).keys()
        if TARGET_START<=d<=TARGET_END
    )
    wanted=set(trading_dates)
    checkpoints=[cp for cp in shadow.make_checkpoints(by) if cp.date().isoformat() in wanted]
    if not checkpoints:
        raise RuntimeError("No checkpoints")

    base=[]
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
            base.append({
                "checkpoint_et":cp.isoformat(),
                "checkpoint_dt":cp,
                "date":cp.date().isoformat(),
                "symbol":sym,
            })

        if i%25==0 or i==len(checkpoints):
            print(f"V2.6 OOS PREP PROGRESS: {i}/{len(checkpoints)}",flush=True)

    if not base:
        raise RuntimeError("No regime BUY rows")

    date_windows=chunk_dates(trading_dates,WINDOW_TRADING_DAYS)
    results={}

    for name,cfg in FIXED_CANDIDATES.items():
        candidate_rows=[r for r in base if r["symbol"] in cfg["symbols"]]
        candidate_rows=dedup(candidate_rows,cfg["dedup_minutes"])

        candidate={}
        for cost_bps in COST_BPS:
            cost=cost_bps/10000.0
            windows=[]
            all_returns=[]

            for wi,dates in enumerate(date_windows,1):
                ds=set(dates)
                rows=[r for r in candidate_rows if r["date"] in ds]
                vals=[]
                by_symbol=Counter()
                for r in rows:
                    ret=fixed_return(index,r["symbol"],r["checkpoint_dt"],cfg["horizon_minutes"])
                    if ret is None:
                        continue
                    vals.append(ret-cost)
                    by_symbol[r["symbol"]]+=1

                s=summarize(vals)
                all_returns.extend(vals)
                windows.append({
                    "window_index":wi,
                    "start_date":dates[0],
                    "end_date":dates[-1],
                    "trading_days":len(dates),
                    "by_symbol":dict(by_symbol),
                    **s,
                    "max_drawdown_simple":max_drawdown_simple(vals) if vals else None,
                })

            positive=[w for w in windows if w["mean"] is not None and w["mean"]>0]
            negative=[w for w in windows if w["mean"] is not None and w["mean"]<=0]
            nonempty=[w for w in windows if w["count"]>0]
            overall=summarize(all_returns)

            candidate[str(cost_bps)]={
                "overall":overall,
                "window_count":len(windows),
                "nonempty_window_count":len(nonempty),
                "positive_window_count":len(positive),
                "negative_window_count":len(negative),
                "positive_window_rate":(
                    len(positive)/len(nonempty) if nonempty else None
                ),
                "worst_window_mean":(
                    min((w["mean"] for w in nonempty), default=None)
                ),
                "best_window_mean":(
                    max((w["mean"] for w in nonempty), default=None)
                ),
                "max_drawdown_simple":max_drawdown_simple(all_returns) if all_returns else None,
                "windows":windows,
            }

        results[name]={
            "definition":{
                "symbols":sorted(cfg["symbols"]),
                "dedup_minutes":cfg["dedup_minutes"],
                "horizon_minutes":cfg["horizon_minutes"],
                "selection_locked_from_v2_5":True,
            },
            "stress":candidate,
        }

    # Pre-registered acceptance-style diagnostics only; no automatic promotion.
    acceptance={}
    for name,data in results.items():
        s5=data["stress"]["5"]
        s10=data["stress"]["10"]
        acceptance[name]={
            "passes_5bps_mean_positive":bool(s5["overall"]["mean"] is not None and s5["overall"]["mean"]>0),
            "passes_5bps_positive_window_rate_ge_0_60":bool(
                s5["positive_window_rate"] is not None and s5["positive_window_rate"]>=0.60
            ),
            "passes_10bps_mean_nonnegative":bool(
                s10["overall"]["mean"] is not None and s10["overall"]["mean"]>=0
            ),
            "observation_count_5bps":s5["overall"]["count"],
            "all_conditions_pass":False,
        }
        acceptance[name]["all_conditions_pass"]=all([
            acceptance[name]["passes_5bps_mean_positive"],
            acceptance[name]["passes_5bps_positive_window_rate_ge_0_60"],
            acceptance[name]["passes_10bps_mean_nonnegative"],
            acceptance[name]["observation_count_5bps"]>=20,
        ])

    report={
        "stage":"V2.6_REGIME_AWARE_BUY_WALKFORWARD_OOS_VALIDATION",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "windowing":{
            "window_trading_days":WINDOW_TRADING_DAYS,
            "time_order_preserved":True,
            "candidate_selection_reopened":False,
            "candidate_parameters_locked_from_v2_5":True,
        },
        "fixed_candidates":results,
        "diagnostic_acceptance":acceptance,
        "interpretation_contract":{
            "oos_validation_only":True,
            "candidate_reoptimized":False,
            "production_change_applied":False,
            "shadow_strategy_enabled":False,
            "paper_submission_enabled":False,
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
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_regime_aware_buy_walkforward_oos_v2_6.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    compact={
        "stage":report["stage"],
        "status":report["status"],
        "windowing":report["windowing"],
        "diagnostic_acceptance":report["diagnostic_acceptance"],
        "MSFT_ONLY_5BPS":results["MSFT_ONLY_30M"]["stress"]["5"],
        "MSFT_ONLY_10BPS":results["MSFT_ONLY_30M"]["stress"]["10"],
        "MSFT_NVDA_5BPS":results["MSFT_NVDA_30M"]["stress"]["5"],
        "MSFT_NVDA_10BPS":results["MSFT_NVDA_30M"]["stress"]["10"],
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
