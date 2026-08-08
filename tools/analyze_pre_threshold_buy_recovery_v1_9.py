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
THRESHOLDS=(0.50,0.55,0.60,0.65,0.70,0.73,0.75)
MIN_RR=1.0


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


def truncate(index,cp):
    out={}
    for sym,(times,rows) in index.items():
        out[sym]=rows[:bisect_right(times,cp)]
    return out


def choose(analyses, threshold, confidence_kind="calibrated"):
    eligible=[]
    for item in analyses:
        action=str(item.get("action","HOLD")).upper()
        if action not in {"BUY","SELL"}:
            continue
        cc=item.get("confidence_calibration",{})
        conf=float(cc.get(
            "raw_confidence" if confidence_kind=="raw" else "calibrated_confidence",0.0
        ))
        rr=float(item.get("reward_risk",0.0))
        if conf>=threshold and rr>=MIN_RR and item.get("execution_mode")=="ANALYSIS_ONLY":
            eligible.append((
                conf,rr,{
                    "symbol":str(item.get("symbol","")).upper(),
                    "side":action,
                    "confidence":conf,
                    "reward_risk":rr,
                    "consensus_score":float(item.get("consensus_score",0.0)),
                }
            ))
    if not eligible:
        return None
    eligible.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return eligible[0][2]


def tf_signature(item):
    return {
        tf.get("timeframe"):{
            "signal":tf.get("signal"),
            "directional_score":tf.get("directional_score"),
            "weight":tf.get("weight"),
            "probability":tf.get("probability"),
        }
        for tf in item.get("timeframes",[])
    }


def build(root:Path):
    root=Path(root).resolve()
    by=load_recovery(root)
    index=build_index(by)
    dates=sorted(shadow.regular_session_rows(by.get("SPY",[])).keys())
    target_dates=[d for d in dates if TARGET_START<=d<=TARGET_END]
    wanted=set(target_dates)
    checkpoints=[cp for cp in shadow.make_checkpoints(by) if cp.date().isoformat() in wanted]
    if not checkpoints:
        raise RuntimeError("No target checkpoints")

    records=[]
    for i,cp in enumerate(checkpoints,1):
        analyses,audit,rejected,canonical=shadow.analyze_at_rows(truncate(index,cp))
        records.append({
            "checkpoint_et":cp.isoformat(),
            "date":cp.date().isoformat(),
            "analyses":analyses,
            "feature_audit":audit,
            "rejected_symbols":rejected,
            "canonical_selected":canonical,
        })
        if i%25==0 or i==len(checkpoints):
            print(f"V1.9 ANALYSIS PROGRESS: {i}/{len(checkpoints)}",flush=True)

    full_coverage=[r for r in records if not r["rejected_symbols"] and len(r["analyses"])==len(shadow.ALLOWED)]
    warmup_deficient=[r for r in records if r not in full_coverage]
    warmup_dates=sorted({r["date"] for r in warmup_deficient})
    normalized_dates=sorted({r["date"] for r in full_coverage})

    sensitivity={}
    for kind in ("calibrated","raw"):
        rows={}
        for th in THRESHOLDS:
            sides=Counter()
            buys=Counter()
            sells=Counter()
            selected_count=0
            for rec in full_coverage:
                sel=choose(rec["analyses"],th,kind)
                if sel:
                    selected_count+=1
                    sides[sel["side"]]+=1
                    if sel["side"]=="BUY": buys[sel["symbol"]]+=1
                    if sel["side"]=="SELL": sells[sel["symbol"]]+=1
            rows[f"{th:.2f}"]={
                "selected_count":selected_count,
                "buy_selected_count":sides.get("BUY",0),
                "sell_selected_count":sides.get("SELL",0),
                "buy_by_symbol":dict(buys),
                "sell_by_symbol":dict(sells),
            }
        sensitivity[kind]=rows

    calibration_effect=[]
    raw_rescued_buy=0
    calibrated_buy=0
    for rec in full_coverage:
        csel=choose(rec["analyses"],0.75,"calibrated")
        rsel=choose(rec["analyses"],0.75,"raw")
        if csel and csel["side"]=="BUY": calibrated_buy+=1
        if rsel and rsel["side"]=="BUY": raw_rescued_buy+=1
        if csel!=rsel:
            calibration_effect.append({
                "checkpoint_et":rec["checkpoint_et"],
                "calibrated_selection":csel,
                "raw_selection":rsel,
            })

    msft_sell_tf=defaultdict(Counter)
    msft_sell_examples=[]
    canonical_side_counts=Counter()
    action_counts_by_symbol=defaultdict(Counter)
    buy_action_rows=[]
    for rec in full_coverage:
        canonical=rec["canonical_selected"]
        if canonical:
            canonical_side_counts[str(canonical.get("side","")).upper()]+=1
        for item in rec["analyses"]:
            sym=str(item.get("symbol","")).upper()
            action=str(item.get("action","HOLD")).upper()
            action_counts_by_symbol[sym][action]+=1
            if action=="BUY":
                cc=item.get("confidence_calibration",{})
                buy_action_rows.append({
                    "checkpoint_et":rec["checkpoint_et"],
                    "symbol":sym,
                    "consensus_score":item.get("consensus_score"),
                    "raw_confidence":cc.get("raw_confidence"),
                    "calibrated_confidence":cc.get("calibrated_confidence"),
                    "calibration_penalty":(
                        float(cc.get("raw_confidence",0.0))-float(cc.get("calibrated_confidence",0.0))
                    ),
                    "reward_risk":item.get("reward_risk"),
                    "timeframe_consensus":item.get("timeframe_consensus"),
                })
            if canonical and str(canonical.get("side","")).upper()=="SELL" and str(canonical.get("symbol","")).upper()=="MSFT" and sym=="MSFT":
                sig=tf_signature(item)
                for tf,v in sig.items():
                    msft_sell_tf[tf][str(v.get("signal","UNKNOWN"))]+=1
                if len(msft_sell_examples)<20:
                    msft_sell_examples.append({
                        "checkpoint_et":rec["checkpoint_et"],
                        "consensus_score":item.get("consensus_score"),
                        "timeframe_consensus":item.get("timeframe_consensus"),
                        "raw_confidence":item.get("confidence_calibration",{}).get("raw_confidence"),
                        "calibrated_confidence":item.get("confidence_calibration",{}).get("calibrated_confidence"),
                        "reward_risk":item.get("reward_risk"),
                        "timeframes":sig,
                    })

    buy_action_rows.sort(
        key=lambda x:(
            float(x.get("calibrated_confidence") or 0),
            float(x.get("reward_risk") or 0)
        ),
        reverse=True
    )

    report={
        "stage":"V1.9_PRE_THRESHOLD_BUY_RECOVERY_COUNTERFACTUAL_AND_1D_WARMUP_NORMALIZATION",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_dataset":RECOVERY_REL,
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "warmup_normalization":{
            "method":"EXCLUDE_ONLY_CHECKPOINTS_WITH_INCOMPLETE_CANONICAL_7TF_FEATURE_SET",
            "synthetic_1d_data_created":False,
            "warmup_deficient_dates":warmup_dates,
            "warmup_deficient_checkpoint_count":len(warmup_deficient),
            "normalized_full_coverage_dates":normalized_dates,
            "normalized_full_coverage_checkpoint_count":len(full_coverage),
        },
        "canonical_baseline_full_coverage":{
            "selected_side_counts":dict(canonical_side_counts),
            "action_counts_by_symbol":{
                s:dict(c) for s,c in sorted(action_counts_by_symbol.items())
            },
            "buy_action_row_count":len(buy_action_rows),
            "top_buy_action_rows":buy_action_rows[:50],
        },
        "confidence_counterfactual":{
            "reward_risk_floor_held_constant":MIN_RR,
            "thresholds_tested":list(THRESHOLDS),
            "calibrated_confidence":sensitivity["calibrated"],
            "raw_confidence":sensitivity["raw"],
            "at_0_75":{
                "canonical_calibrated_buy_selected_count":calibrated_buy,
                "raw_confidence_buy_selected_count":raw_rescued_buy,
                "selection_changed_checkpoint_count":len(calibration_effect),
                "selection_change_examples":calibration_effect[:100],
            },
        },
        "msft_sell_bias_decomposition":{
            "canonical_msft_sell_selected_count":sum(
                1 for r in full_coverage
                if r["canonical_selected"]
                and str(r["canonical_selected"].get("side","")).upper()=="SELL"
                and str(r["canonical_selected"].get("symbol","")).upper()=="MSFT"
            ),
            "timeframe_signal_counts_on_msft_selected_sell":{
                tf:dict(c) for tf,c in sorted(msft_sell_tf.items())
            },
            "examples":msft_sell_examples,
        },
        "interpretation_contract":{
            "counterfactual_only":True,
            "threshold_change_applied_to_production":False,
            "raw_confidence_applied_to_production":False,
            "warmup_data_imputed":False,
            "automatic_strategy_change":False,
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
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_pre_threshold_buy_recovery_v1_9.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    compact={
        "stage":report["stage"],
        "status":report["status"],
        "warmup_normalization":report["warmup_normalization"],
        "canonical_baseline_full_coverage":{
            "selected_side_counts":report["canonical_baseline_full_coverage"]["selected_side_counts"],
            "action_counts_by_symbol":report["canonical_baseline_full_coverage"]["action_counts_by_symbol"],
            "buy_action_row_count":report["canonical_baseline_full_coverage"]["buy_action_row_count"],
        },
        "confidence_counterfactual":{
            "calibrated_confidence":sensitivity["calibrated"],
            "raw_confidence":sensitivity["raw"],
            "at_0_75":{
                k:v for k,v in report["confidence_counterfactual"]["at_0_75"].items()
                if k!="selection_change_examples"
            },
        },
        "msft_sell_timeframe_counts":report["msft_sell_bias_decomposition"]["timeframe_signal_counts_on_msft_selected_sell"],
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
