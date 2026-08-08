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
MIN_CONF=0.75
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


def trunc(index,cp):
    out={}
    for sym,(times,rows) in index.items():
        out[sym]=rows[:bisect_right(times,cp)]
    return out


def rank_key(item):
    cc=item.get("confidence_calibration",{})
    conf=float(cc.get("calibrated_confidence",0.0))
    rr=float(item.get("reward_risk",0.0))
    return (conf,rr)


def eligible(item):
    action=str(item.get("action","HOLD")).upper()
    cc=item.get("confidence_calibration",{})
    conf=float(cc.get("calibrated_confidence",0.0))
    rr=float(item.get("reward_risk",0.0))
    guard=item.get("execution_mode")=="ANALYSIS_ONLY"
    return action in {"BUY","SELL"} and conf>=MIN_CONF and rr>=MIN_RR and guard


def build(root:Path):
    root=Path(root).resolve()
    by=load_recovery(root)
    index=build_index(by)
    dates=sorted(shadow.regular_session_rows(by.get("SPY",[])).keys())
    target_dates=[d for d in dates if TARGET_START<=d<=TARGET_END]
    wanted=set(target_dates)
    checkpoints=[cp for cp in shadow.make_checkpoints(by) if cp.date().isoformat() in wanted]
    if not checkpoints:
        raise RuntimeError("No full-coverage checkpoints found")

    funnel=Counter()
    by_symbol=defaultdict(Counter)
    rr_values=[]
    conf_values=[]
    eligible_buy_rows=[]
    ranking_losses=[]
    buy_rows=[]
    checkpoint_summaries=[]

    for i,cp in enumerate(checkpoints,1):
        analyses,audit,rejected,selected=shadow.analyze_at_rows(trunc(index,cp))
        if rejected or len(analyses)!=len(shadow.ALLOWED):
            continue

        eligible_rows=[x for x in analyses if eligible(x)]
        ranked=sorted(eligible_rows,key=rank_key,reverse=True)
        winner=ranked[0] if ranked else None

        cp_summary={
            "checkpoint_et":cp.isoformat(),
            "winner":None if winner is None else {
                "symbol":winner.get("symbol"),
                "action":winner.get("action"),
                "confidence":rank_key(winner)[0],
                "reward_risk":rank_key(winner)[1],
            },
            "eligible_count":len(ranked),
            "eligible_buy_count":sum(1 for x in ranked if str(x.get("action","")).upper()=="BUY"),
            "eligible_sell_count":sum(1 for x in ranked if str(x.get("action","")).upper()=="SELL"),
        }

        for item in analyses:
            if str(item.get("action","HOLD")).upper()!="BUY":
                continue

            sym=str(item.get("symbol","")).upper()
            cc=item.get("confidence_calibration",{})
            conf=float(cc.get("calibrated_confidence",0.0))
            raw=float(cc.get("raw_confidence",0.0))
            rr=float(item.get("reward_risk",0.0))
            guard=item.get("execution_mode")=="ANALYSIS_ONLY"
            conf_pass=conf>=MIN_CONF
            rr_pass=rr>=MIN_RR

            if not conf_pass and not rr_pass:
                bucket="FAIL_CONFIDENCE_AND_RR"
            elif not conf_pass:
                bucket="FAIL_CONFIDENCE_ONLY"
            elif not rr_pass:
                bucket="FAIL_RR_ONLY"
            elif not guard:
                bucket="FAIL_GUARDRAIL"
            else:
                if winner is None:
                    bucket="PASS_ALL_BUT_NO_WINNER_ANOMALY"
                elif winner is item:
                    bucket="PASS_ALL_AND_WINNER"
                elif str(winner.get("action","")).upper()=="SELL":
                    bucket="PASS_ALL_BUT_LOST_TO_SELL_RANKING"
                else:
                    bucket="PASS_ALL_BUT_LOST_TO_BUY_RANKING"

            funnel[bucket]+=1
            by_symbol[sym][bucket]+=1
            rr_values.append(rr)
            conf_values.append(conf)

            row={
                "checkpoint_et":cp.isoformat(),
                "symbol":sym,
                "bucket":bucket,
                "consensus_score":item.get("consensus_score"),
                "raw_confidence":raw,
                "calibrated_confidence":conf,
                "confidence_margin":conf-MIN_CONF,
                "reward_risk":rr,
                "reward_risk_margin":rr-MIN_RR,
                "timeframe_consensus":item.get("timeframe_consensus"),
            }
            buy_rows.append(row)

            if conf_pass and rr_pass and guard:
                eligible_buy_rows.append(row)
                if bucket=="PASS_ALL_BUT_LOST_TO_SELL_RANKING":
                    ranking_losses.append({
                        **row,
                        "winner_symbol":winner.get("symbol"),
                        "winner_action":winner.get("action"),
                        "winner_confidence":rank_key(winner)[0],
                        "winner_reward_risk":rank_key(winner)[1],
                        "confidence_gap_to_winner":rank_key(winner)[0]-conf,
                        "rr_gap_to_winner":rank_key(winner)[1]-rr,
                    })

        checkpoint_summaries.append(cp_summary)
        if i%25==0 or i==len(checkpoints):
            print(f"V2.0 FUNNEL PROGRESS: {i}/{len(checkpoints)}",flush=True)

    if not buy_rows:
        raise RuntimeError("No BUY action rows found")

    rr_sorted=sorted(rr_values)
    conf_sorted=sorted(conf_values)
    loss_conf_gaps=[x["confidence_gap_to_winner"] for x in ranking_losses]
    loss_rr_gaps=[x["rr_gap_to_winner"] for x in ranking_losses]

    report={
        "stage":"V2.0_BUY_CANDIDATE_REJECTION_FUNNEL_AND_REWARD_RISK_ROOT_CAUSE_AUDIT",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_range":{"start":TARGET_START,"end":TARGET_END},
        "source_dataset":RECOVERY_REL,
        "thresholds_observed_not_modified":{
            "min_confidence":MIN_CONF,
            "min_reward_risk":MIN_RR,
        },
        "buy_funnel":{
            "total_buy_action_rows":len(buy_rows),
            "bucket_counts":dict(funnel),
            "bucket_counts_by_symbol":{
                s:dict(c) for s,c in sorted(by_symbol.items())
            },
            "all_thresholds_pass_count":len(eligible_buy_rows),
            "ranking_loss_to_sell_count":len(ranking_losses),
            "actual_buy_winner_count":funnel.get("PASS_ALL_AND_WINNER",0),
        },
        "reward_risk_diagnostics":{
            "buy_rr_min":min(rr_sorted),
            "buy_rr_median":statistics.median(rr_sorted),
            "buy_rr_mean":statistics.mean(rr_sorted),
            "buy_rr_max":max(rr_sorted),
            "buy_rr_ge_1_count":sum(1 for x in rr_sorted if x>=MIN_RR),
            "buy_rr_lt_1_count":sum(1 for x in rr_sorted if x<MIN_RR),
        },
        "confidence_diagnostics":{
            "buy_conf_min":min(conf_sorted),
            "buy_conf_median":statistics.median(conf_sorted),
            "buy_conf_mean":statistics.mean(conf_sorted),
            "buy_conf_max":max(conf_sorted),
            "buy_conf_ge_075_count":sum(1 for x in conf_sorted if x>=MIN_CONF),
            "buy_conf_lt_075_count":sum(1 for x in conf_sorted if x<MIN_CONF),
        },
        "ranking_loss_diagnostics":{
            "count":len(ranking_losses),
            "median_confidence_gap_to_sell_winner":statistics.median(loss_conf_gaps) if loss_conf_gaps else None,
            "max_confidence_gap_to_sell_winner":max(loss_conf_gaps) if loss_conf_gaps else None,
            "median_rr_gap_to_sell_winner":statistics.median(loss_rr_gaps) if loss_rr_gaps else None,
            "examples":ranking_losses[:100],
        },
        "checkpoint_summary":{
            "full_coverage_checkpoint_count":len(checkpoint_summaries),
            "checkpoints_with_eligible_buy":sum(1 for x in checkpoint_summaries if x["eligible_buy_count"]>0),
            "checkpoints_with_eligible_sell":sum(1 for x in checkpoint_summaries if x["eligible_sell_count"]>0),
            "checkpoints_with_no_eligible_candidate":sum(1 for x in checkpoint_summaries if x["eligible_count"]==0),
        },
        "interpretation_contract":{
            "diagnostic_only":True,
            "threshold_change_applied":False,
            "selector_ranking_change_applied":False,
            "reward_risk_formula_change_applied":False,
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
        "checkpoint_rows":checkpoint_summaries,
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_buy_rejection_funnel_v2_0.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    print(json.dumps({
        "stage":report["stage"],
        "status":report["status"],
        "buy_funnel":report["buy_funnel"],
        "reward_risk_diagnostics":report["reward_risk_diagnostics"],
        "confidence_diagnostics":report["confidence_diagnostics"],
        "ranking_loss_diagnostics":{
            k:v for k,v in report["ranking_loss_diagnostics"].items() if k!="examples"
        },
        "checkpoint_summary":report["checkpoint_summary"],
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
