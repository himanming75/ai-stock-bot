from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse, json, sys, statistics

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow

TARGET_START="2026-06-15"
TARGET_END="2026-07-07"
RECOVERY_REL="runtime/v1_7_3_holdout_recovery/alpaca_real_historical_holdout_75d.jsonl"
TIMEFRAMES=("1m","3m","5m","15m","30m","1h","1d")


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
        sym:([shadow.parse_timestamp(r["timestamp"]).astimezone(shadow.ET) for r in rows],rows)
        for sym,rows in by.items()
    }


def trunc(index,cp):
    return {
        sym: rows[:bisect_right(times,cp)]
        for sym,(times,rows) in index.items()
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


def row_from_item(cp,item):
    tf_map={str(x.get("timeframe")):x for x in item.get("timeframes",[])}
    contributions={}
    signed=[]
    abs_sum=0.0
    same_sign=0.0
    opposite_sign=0.0
    action=str(item.get("action","HOLD")).upper()
    action_sign=1.0 if action=="BUY" else -1.0 if action=="SELL" else 0.0

    for tf in TIMEFRAMES:
        x=tf_map.get(tf,{})
        weight=float(x.get("weight",0.0))
        er=float(x.get("expected_return",0.0))
        contribution=er*weight
        contributions[tf]={
            "weight":weight,
            "signal":x.get("signal"),
            "directional_score":float(x.get("directional_score",0.0)),
            "expected_return":er,
            "weighted_expected_return":contribution,
        }
        signed.append(contribution)
        abs_sum += abs(contribution)
        if action_sign and contribution*action_sign>0:
            same_sign += abs(contribution)
        elif action_sign and contribution*action_sign<0:
            opposite_sign += abs(contribution)

    net=sum(signed)
    cancellation=(1.0-(abs(net)/abs_sum)) if abs_sum else 0.0

    return {
        "checkpoint_et":cp.isoformat(),
        "date":cp.date().isoformat(),
        "symbol":str(item.get("symbol","")).upper(),
        "action":action,
        "consensus_score":float(item.get("consensus_score",0.0)),
        "expected_return":float(item.get("expected_return",0.0)),
        "abs_expected_return":abs(float(item.get("expected_return",0.0))),
        "expected_risk":float(item.get("expected_risk",0.0)),
        "reward_risk":float(item.get("reward_risk",0.0)),
        "same_direction_contribution_abs":same_sign,
        "opposite_direction_contribution_abs":opposite_sign,
        "absolute_contribution_sum":abs_sum,
        "cancellation_ratio":cancellation,
        "timeframes":contributions,
    }


def summarize(rows):
    by_tf={}
    for tf in TIMEFRAMES:
        contrib=[r["timeframes"][tf]["weighted_expected_return"] for r in rows]
        abs_contrib=[abs(x) for x in contrib]
        signal_counts=Counter(str(r["timeframes"][tf]["signal"]) for r in rows)
        by_tf[tf]={
            "weighted_expected_return":stats(contrib),
            "absolute_weighted_contribution":stats(abs_contrib),
            "signal_counts":dict(signal_counts),
            "mean_share_of_absolute_contribution":(
                statistics.mean([
                    abs(r["timeframes"][tf]["weighted_expected_return"])/r["absolute_contribution_sum"]
                    for r in rows if r["absolute_contribution_sum"]>0
                ]) if rows else None
            ),
        }

    return {
        "count":len(rows),
        "expected_return":stats([r["expected_return"] for r in rows]),
        "abs_expected_return":stats([r["abs_expected_return"] for r in rows]),
        "reward_risk":stats([r["reward_risk"] for r in rows]),
        "cancellation_ratio":stats([r["cancellation_ratio"] for r in rows]),
        "same_direction_contribution_abs":stats([r["same_direction_contribution_abs"] for r in rows]),
        "opposite_direction_contribution_abs":stats([r["opposite_direction_contribution_abs"] for r in rows]),
        "timeframe_decomposition":by_tf,
    }


def build(root:Path):
    root=Path(root).resolve()
    by=load_recovery(root)
    index=build_index(by)
    dates=sorted(shadow.regular_session_rows(by.get("SPY",[])).keys())
    wanted={d for d in dates if TARGET_START<=d<=TARGET_END}
    checkpoints=[cp for cp in shadow.make_checkpoints(by) if cp.date().isoformat() in wanted]
    if not checkpoints:
        raise RuntimeError("No full-coverage checkpoints")

    buy_rows=[]
    sell_rows=[]
    by_symbol={"BUY":defaultdict(list),"SELL":defaultdict(list)}
    conflict_patterns={"BUY":Counter(),"SELL":Counter()}

    for i,cp in enumerate(checkpoints,1):
        analyses,_,rejected,_=shadow.analyze_at_rows(trunc(index,cp))
        if rejected or len(analyses)!=len(shadow.ALLOWED):
            continue

        for item in analyses:
            action=str(item.get("action","HOLD")).upper()
            if action not in {"BUY","SELL"}:
                continue
            row=row_from_item(cp,item)
            if action=="BUY":
                buy_rows.append(row)
            else:
                sell_rows.append(row)
            by_symbol[action][row["symbol"]].append(row)

            sigs=tuple(row["timeframes"][tf]["signal"] for tf in TIMEFRAMES)
            conflict_patterns[action][str(sigs)]+=1

        if i%25==0 or i==len(checkpoints):
            print(f"V2.2 CONTRIBUTION PROGRESS: {i}/{len(checkpoints)}",flush=True)

    if not buy_rows or not sell_rows:
        raise RuntimeError("BUY or SELL rows missing")

    buy_summary=summarize(buy_rows)
    sell_summary=summarize(sell_rows)

    report={
        "stage":"V2.2_EXPECTED_RETURN_CANCELLATION_AND_TIMEFRAME_CONTRIBUTION_AUDIT",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "buy_summary":buy_summary,
        "sell_summary":sell_summary,
        "comparison":{
            "mean_abs_expected_return_buy_over_sell":(
                buy_summary["abs_expected_return"]["mean"]/
                sell_summary["abs_expected_return"]["mean"]
            ),
            "mean_cancellation_buy_over_sell":(
                buy_summary["cancellation_ratio"]["mean"]/
                sell_summary["cancellation_ratio"]["mean"]
                if sell_summary["cancellation_ratio"]["mean"] else None
            ),
            "mean_opposite_contribution_buy_over_sell":(
                buy_summary["opposite_direction_contribution_abs"]["mean"]/
                sell_summary["opposite_direction_contribution_abs"]["mean"]
                if sell_summary["opposite_direction_contribution_abs"]["mean"] else None
            ),
        },
        "by_symbol":{
            side:{
                sym:summarize(rows)
                for sym,rows in sorted(group.items())
            }
            for side,group in by_symbol.items()
        },
        "top_conflict_patterns":{
            side:[
                {"pattern":pat,"count":count}
                for pat,count in counts.most_common(20)
            ]
            for side,counts in conflict_patterns.items()
        },
        "interpretation_contract":{
            "diagnostic_only":True,
            "timeframe_weights_changed":False,
            "expected_return_formula_changed":False,
            "rr_formula_changed":False,
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
            "duplicate_engine_created":False,
            "automatic_promotion":False,
        },
        "buy_rows":buy_rows,
        "sell_rows":sell_rows,
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_expected_return_cancellation_v2_2.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    compact={
        "stage":report["stage"],
        "status":report["status"],
        "buy_summary":{
            "count":buy_summary["count"],
            "abs_expected_return":buy_summary["abs_expected_return"],
            "reward_risk":buy_summary["reward_risk"],
            "cancellation_ratio":buy_summary["cancellation_ratio"],
            "opposite_direction_contribution_abs":buy_summary["opposite_direction_contribution_abs"],
            "timeframe_decomposition":buy_summary["timeframe_decomposition"],
        },
        "sell_summary":{
            "count":sell_summary["count"],
            "abs_expected_return":sell_summary["abs_expected_return"],
            "reward_risk":sell_summary["reward_risk"],
            "cancellation_ratio":sell_summary["cancellation_ratio"],
            "opposite_direction_contribution_abs":sell_summary["opposite_direction_contribution_abs"],
            "timeframe_decomposition":sell_summary["timeframe_decomposition"],
        },
        "comparison":report["comparison"],
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
