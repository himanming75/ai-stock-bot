from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import timedelta, datetime, timezone
from pathlib import Path
import argparse, json, sys, statistics

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow

TARGET_START="2026-06-15"
TARGET_END="2026-07-07"
RECOVERY_REL="runtime/v1_7_3_holdout_recovery/alpaca_real_historical_holdout_75d.jsonl"

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


def future_path(index,symbol,cp):
    times,rows=index[symbol]
    start=bisect_right(times,cp)
    cutoff=cp+timedelta(minutes=MAX_HOLD_MINUTES)
    end=bisect_right(times,cutoff)
    return list(zip(times[start:end],rows[start:end]))


def evaluate_long_path(index,symbol,cp):
    path=future_path(index,symbol,cp)
    if not path:
        return None

    # Entry uses first available 1m bar after decision checkpoint.
    entry_time,entry_bar=path[0]
    entry=float(entry_bar["open"])
    tp=entry*(1.0+TP_PCT)
    sl=entry*(1.0-SL_PCT)

    exit_reason="TIME"
    exit_price=float(path[-1][1]["close"])
    exit_time=path[-1][0]

    max_high=entry
    min_low=entry
    for t,b in path:
        high=float(b["high"])
        low=float(b["low"])
        max_high=max(max_high,high)
        min_low=min(min_low,low)

        # Conservative same-bar ambiguity rule: if TP and SL both touch,
        # classify SL first. This avoids optimistic counterfactual bias.
        sl_hit=low<=sl
        tp_hit=high>=tp
        if sl_hit:
            exit_reason="SL"
            exit_price=sl
            exit_time=t
            break
        if tp_hit:
            exit_reason="TP"
            exit_price=tp
            exit_time=t
            break

    realized=(exit_price-entry)/entry
    mfe=(max_high-entry)/entry
    mae=(min_low-entry)/entry
    return {
        "entry_time_et":entry_time.isoformat(),
        "entry_price":entry,
        "exit_time_et":exit_time.isoformat(),
        "exit_price":exit_price,
        "exit_reason":exit_reason,
        "realized_return":realized,
        "mfe":mfe,
        "mae":mae,
        "path_bar_count":len(path),
    }


def stats(vals):
    vals=[float(x) for x in vals]
    if not vals:
        return {"count":0,"min":None,"median":None,"mean":None,"max":None}
    return {
        "count":len(vals),
        "min":min(vals),
        "median":statistics.median(vals),
        "mean":statistics.mean(vals),
        "max":max(vals),
    }


def summarize(rows):
    exits=Counter(r["outcome"]["exit_reason"] for r in rows)
    returns=[r["outcome"]["realized_return"] for r in rows]
    mfes=[r["outcome"]["mfe"] for r in rows]
    maes=[r["outcome"]["mae"] for r in rows]
    wins=sum(1 for x in returns if x>0)
    losses=sum(1 for x in returns if x<0)
    flats=len(returns)-wins-losses
    return {
        "count":len(rows),
        "exit_counts":dict(exits),
        "win_count":wins,
        "loss_count":losses,
        "flat_count":flats,
        "win_rate":wins/len(rows) if rows else None,
        "mean_realized_return":statistics.mean(returns) if returns else None,
        "median_realized_return":statistics.median(returns) if returns else None,
        "cumulative_simple_return":sum(returns) if returns else None,
        "mfe":stats(mfes),
        "mae":stats(maes),
    }


def classify_1d(item):
    one=next((x for x in item.get("timeframes",[]) if x.get("timeframe")=="1d"),None)
    if not one:
        return "MISSING"
    sig=str(one.get("signal","HOLD")).upper()
    if sig=="BUY":
        return "1D_ALIGNED_BUY"
    if sig=="SELL":
        return "1D_OPPOSITE_SELL"
    return "1D_HOLD"


def build(root:Path):
    root=Path(root).resolve()
    by=load_recovery(root)
    index=build_index(by)
    dates=sorted(shadow.regular_session_rows(by.get("SPY",[])).keys())
    wanted={d for d in dates if TARGET_START<=d<=TARGET_END}
    checkpoints=[cp for cp in shadow.make_checkpoints(by) if cp.date().isoformat() in wanted]
    if not checkpoints:
        raise RuntimeError("No target checkpoints")

    groups=defaultdict(list)
    all_rows=[]
    by_symbol=defaultdict(lambda:defaultdict(list))

    for i,cp in enumerate(checkpoints,1):
        analyses,_,rejected,_=shadow.analyze_at_rows(trunc(index,cp))
        if rejected or len(analyses)!=len(shadow.ALLOWED):
            continue

        for item in analyses:
            if str(item.get("action","HOLD")).upper()!="BUY":
                continue
            symbol=str(item.get("symbol","")).upper()
            outcome=evaluate_long_path(index,symbol,cp)
            if not outcome:
                continue
            group=classify_1d(item)
            one=next((x for x in item.get("timeframes",[]) if x.get("timeframe")=="1d"),{})
            row={
                "checkpoint_et":cp.isoformat(),
                "date":cp.date().isoformat(),
                "symbol":symbol,
                "group":group,
                "consensus_score":float(item.get("consensus_score",0.0)),
                "reward_risk":float(item.get("reward_risk",0.0)),
                "calibrated_confidence":float(
                    item.get("confidence_calibration",{}).get("calibrated_confidence",0.0)
                ),
                "one_day_signal":one.get("signal"),
                "one_day_directional_score":float(one.get("directional_score",0.0)),
                "one_day_expected_return":float(one.get("expected_return",0.0)),
                "outcome":outcome,
            }
            groups[group].append(row)
            by_symbol[symbol][group].append(row)
            all_rows.append(row)

        if i%25==0 or i==len(checkpoints):
            print(f"V2.3 OUTCOME PROGRESS: {i}/{len(checkpoints)}",flush=True)

    if not all_rows:
        raise RuntimeError("No BUY outcome rows")

    summaries={g:summarize(rows) for g,rows in sorted(groups.items())}
    symbol_summaries={
        sym:{g:summarize(rows) for g,rows in sorted(gs.items())}
        for sym,gs in sorted(by_symbol.items())
    }

    report={
        "stage":"V2.3_1D_REGIME_CONFLICT_COUNTERFACTUAL_AND_BUY_OUTCOME_VALIDATION",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "counterfactual_contract":{
            "direction":"LONG_ONLY_BUY_ACTION_ROWS",
            "entry_rule":"FIRST_1M_BAR_OPEN_AFTER_CHECKPOINT",
            "take_profit_pct":TP_PCT,
            "stop_loss_pct":SL_PCT,
            "max_hold_minutes":MAX_HOLD_MINUTES,
            "same_bar_tp_sl_ambiguity_rule":"SL_FIRST_CONSERVATIVE",
            "production_lifecycle_replaced":False,
            "diagnostic_path_evaluator_only":True,
        },
        "group_summaries":summaries,
        "symbol_group_summaries":symbol_summaries,
        "overall":summarize(all_rows),
        "interpretation_contract":{
            "diagnostic_only":True,
            "one_day_weight_changed":False,
            "one_day_signal_ignored_in_production":False,
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
        "rows":all_rows,
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_1d_regime_conflict_outcome_v2_3.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    print(json.dumps({
        "stage":report["stage"],
        "status":report["status"],
        "counterfactual_contract":report["counterfactual_contract"],
        "group_summaries":report["group_summaries"],
        "overall":report["overall"],
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
