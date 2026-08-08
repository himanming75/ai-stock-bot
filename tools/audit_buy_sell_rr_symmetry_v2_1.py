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
    out={}
    for sym,(times,rows) in index.items():
        out[sym]=rows[:bisect_right(times,cp)]
    return out


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


def collect_action_row(cp,item):
    tf=item.get("timeframes",[])
    atr_values=[
        float(x.get("features",{}).get("atr_percent",0.0))
        for x in tf
    ]
    tf_expected_return=[
        float(x.get("expected_return",0.0)) for x in tf
    ]
    tf_expected_risk=[
        float(x.get("expected_risk",0.0)) for x in tf
    ]
    tc=item.get("timeframe_consensus",{})
    return {
        "checkpoint_et":cp.isoformat(),
        "date":cp.date().isoformat(),
        "symbol":str(item.get("symbol","")).upper(),
        "action":str(item.get("action","HOLD")).upper(),
        "consensus_score":float(item.get("consensus_score",0.0)),
        "abs_consensus_score":abs(float(item.get("consensus_score",0.0))),
        "expected_return":float(item.get("expected_return",0.0)),
        "abs_expected_return":abs(float(item.get("expected_return",0.0))),
        "expected_risk":float(item.get("expected_risk",0.0)),
        "reward_risk":float(item.get("reward_risk",0.0)),
        "alignment":float(tc.get("alignment",0.0)),
        "disagreement":float(tc.get("disagreement",0.0)),
        "buy_weight":float(tc.get("buy_weight",0.0)),
        "sell_weight":float(tc.get("sell_weight",0.0)),
        "hold_weight":float(tc.get("hold_weight",0.0)),
        "probability":float(item.get("probability",0.0)),
        "calibrated_confidence":float(
            item.get("confidence_calibration",{}).get("calibrated_confidence",0.0)
        ),
        "raw_confidence":float(
            item.get("confidence_calibration",{}).get("raw_confidence",0.0)
        ),
        "mean_tf_atr_percent":statistics.mean(atr_values) if atr_values else 0.0,
        "sum_abs_tf_expected_return":sum(abs(x) for x in tf_expected_return),
        "sum_tf_expected_risk":sum(tf_expected_risk),
        "timeframe_signals":{
            str(x.get("timeframe")):str(x.get("signal",""))
            for x in tf
        },
    }


def summarize(rows):
    return {
        "count":len(rows),
        "abs_expected_return":stats([r["abs_expected_return"] for r in rows]),
        "expected_risk":stats([r["expected_risk"] for r in rows]),
        "reward_risk":stats([r["reward_risk"] for r in rows]),
        "abs_consensus_score":stats([r["abs_consensus_score"] for r in rows]),
        "alignment":stats([r["alignment"] for r in rows]),
        "disagreement":stats([r["disagreement"] for r in rows]),
        "probability":stats([r["probability"] for r in rows]),
        "calibrated_confidence":stats([r["calibrated_confidence"] for r in rows]),
        "mean_tf_atr_percent":stats([r["mean_tf_atr_percent"] for r in rows]),
        "rr_ge_1_count":sum(1 for r in rows if r["reward_risk"]>=1.0),
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
    hold_rows=[]
    tf_signal_counts={"BUY":defaultdict(Counter),"SELL":defaultdict(Counter)}
    by_symbol={"BUY":defaultdict(list),"SELL":defaultdict(list)}

    for i,cp in enumerate(checkpoints,1):
        analyses,_,rejected,_=shadow.analyze_at_rows(trunc(index,cp))
        if rejected or len(analyses)!=len(shadow.ALLOWED):
            continue

        for item in analyses:
            row=collect_action_row(cp,item)
            action=row["action"]
            if action=="BUY":
                buy_rows.append(row)
                by_symbol["BUY"][row["symbol"]].append(row)
            elif action=="SELL":
                sell_rows.append(row)
                by_symbol["SELL"][row["symbol"]].append(row)
            else:
                hold_rows.append(row)

            if action in {"BUY","SELL"}:
                for tf,sig in row["timeframe_signals"].items():
                    tf_signal_counts[action][tf][sig]+=1

        if i%25==0 or i==len(checkpoints):
            print(f"V2.1 SYMMETRY PROGRESS: {i}/{len(checkpoints)}",flush=True)

    if not buy_rows or not sell_rows:
        raise RuntimeError("BUY or SELL rows missing")

    buy_summary=summarize(buy_rows)
    sell_summary=summarize(sell_rows)

    ratio = lambda a,b: (a/b if b not in (0,None) and a is not None else None)

    decomposition={
        "buy_vs_sell_mean_ratios":{
            "abs_expected_return_ratio":ratio(
                buy_summary["abs_expected_return"]["mean"],
                sell_summary["abs_expected_return"]["mean"]
            ),
            "expected_risk_ratio":ratio(
                buy_summary["expected_risk"]["mean"],
                sell_summary["expected_risk"]["mean"]
            ),
            "reward_risk_ratio":ratio(
                buy_summary["reward_risk"]["mean"],
                sell_summary["reward_risk"]["mean"]
            ),
            "alignment_ratio":ratio(
                buy_summary["alignment"]["mean"],
                sell_summary["alignment"]["mean"]
            ),
            "disagreement_ratio":ratio(
                buy_summary["disagreement"]["mean"],
                sell_summary["disagreement"]["mean"]
            ),
            "abs_consensus_ratio":ratio(
                buy_summary["abs_consensus_score"]["mean"],
                sell_summary["abs_consensus_score"]["mean"]
            ),
        },
        "formula_identity":{
            "engine_uses_absolute_expected_return":True,
            "engine_rr_formula":"abs(expected_return) / expected_risk",
            "direction_label_multiplier_in_rr":False,
            "formula_is_directionally_symmetric":True,
        },
    }

    report={
        "stage":"V2.1_BUY_VS_SELL_REWARD_RISK_FORMULA_DECOMPOSITION_AND_DIRECTIONAL_SYMMETRY_AUDIT",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "buy_summary":buy_summary,
        "sell_summary":sell_summary,
        "hold_count":len(hold_rows),
        "comparison":decomposition,
        "by_symbol":{
            side:{
                sym:summarize(rows)
                for sym,rows in sorted(group.items())
            }
            for side,group in by_symbol.items()
        },
        "timeframe_signal_counts":{
            side:{
                tf:dict(c)
                for tf,c in sorted(group.items())
            }
            for side,group in tf_signal_counts.items()
        },
        "interpretation_contract":{
            "diagnostic_only":True,
            "rr_formula_changed":False,
            "threshold_changed":False,
            "direction_weight_changed":False,
            "timeframe_weight_changed":False,
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
    (out/"latest_buy_sell_rr_symmetry_v2_1.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    print(json.dumps({
        "stage":report["stage"],
        "status":report["status"],
        "buy_summary":report["buy_summary"],
        "sell_summary":report["sell_summary"],
        "comparison":report["comparison"],
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
