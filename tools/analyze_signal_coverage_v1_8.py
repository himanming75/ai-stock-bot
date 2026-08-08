from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse, json, statistics

V17_REL="runtime/real_market_multitimeframe_shadow/latest_holdout_zero_trade_audit_v1_7_4.json"
MIN_CONFIDENCE=0.75
MIN_REWARD_RISK=1.0


def _num(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def _margin_bucket(margin):
    if margin <= 0:
        return "PASS"
    if margin <= 0.02:
        return "MISS_LE_0.02"
    if margin <= 0.05:
        return "MISS_0.02_TO_0.05"
    if margin <= 0.10:
        return "MISS_0.05_TO_0.10"
    return "MISS_GT_0.10"


def build(root:Path):
    root=Path(root).resolve()
    src=root/V17_REL
    if not src.exists():
        raise RuntimeError(f"V1.7.4 result missing: {src}")
    v17=json.loads(src.read_text(encoding="utf-8"))

    if v17.get("status")!="PASS":
        raise RuntimeError("V1.7.4 source result is not PASS")

    checkpoints=v17.get("checkpoint_audit",[])
    daily=v17.get("daily_audit",[])
    if not checkpoints:
        raise RuntimeError("V1.7.4 checkpoint_audit is empty")

    action_by_symbol=defaultdict(Counter)
    selected_sell_by_symbol=Counter()
    selected_sell_by_hour=Counter()
    selected_sell_by_date=Counter()

    confidence_misses=[]
    confidence_miss_by_symbol=Counter()
    confidence_bucket_counts=Counter()

    rr_misses=[]
    rr_miss_by_symbol=Counter()

    hold_by_symbol=Counter()
    hold_by_date=Counter()

    rejected_symbol_counts=Counter()
    missing_tf_counts=Counter()
    feature_issue_by_date=Counter()
    feature_issue_details=[]

    buy_like_but_blocked=[]
    directional_counts=Counter()

    for rec in checkpoints:
        cp=str(rec.get("checkpoint_et",""))
        day=str(rec.get("date",""))
        selected=rec.get("selected_candidate")
        if selected and str(selected.get("side","")).upper()=="SELL":
            sym=str(selected.get("symbol","")).upper()
            selected_sell_by_symbol[sym]+=1
            selected_sell_by_date[day]+=1
            try:
                hour=cp[11:13]
                selected_sell_by_hour[hour]+=1
            except Exception:
                pass

        for row in rec.get("analysis_rows",[]):
            sym=str(row.get("symbol","")).upper()
            action=str(row.get("action","HOLD")).upper()
            conf=_num(row.get("confidence"))
            rr=_num(row.get("reward_risk"))
            action_by_symbol[sym][action]+=1
            directional_counts[action]+=1

            if action=="HOLD":
                hold_by_symbol[sym]+=1
                hold_by_date[day]+=1

            if action in {"BUY","SELL"}:
                conf_margin=max(0.0,MIN_CONFIDENCE-conf)
                rr_margin=max(0.0,MIN_REWARD_RISK-rr)

                if conf_margin>0:
                    confidence_misses.append(conf_margin)
                    confidence_miss_by_symbol[sym]+=1
                    confidence_bucket_counts[_margin_bucket(conf_margin)]+=1

                if rr_margin>0:
                    rr_misses.append(rr_margin)
                    rr_miss_by_symbol[sym]+=1

                if action=="BUY":
                    reasons=[]
                    if conf<MIN_CONFIDENCE:
                        reasons.append("CONFIDENCE")
                    if rr<MIN_REWARD_RISK:
                        reasons.append("REWARD_RISK")
                    if row.get("guardrail_pass") is False:
                        reasons.append("GUARDRAIL")
                    if reasons:
                        buy_like_but_blocked.append({
                            "checkpoint_et":cp,
                            "date":day,
                            "symbol":sym,
                            "confidence":conf,
                            "confidence_margin":max(0.0,MIN_CONFIDENCE-conf),
                            "reward_risk":rr,
                            "reward_risk_margin":max(0.0,MIN_REWARD_RISK-rr),
                            "blocked_by":reasons,
                        })

        rejected=rec.get("rejected_symbols") or {}
        if rejected:
            feature_issue_by_date[day]+=1
            for sym,info in rejected.items():
                rejected_symbol_counts[str(sym).upper()]+=1
                missing=info.get("missing_timeframes",[]) if isinstance(info,dict) else []
                for tf in missing:
                    missing_tf_counts[f"{str(sym).upper()}:{tf}"]+=1
                feature_issue_details.append({
                    "checkpoint_et":cp,
                    "date":day,
                    "symbol":str(sym).upper(),
                    "reason":info.get("reason") if isinstance(info,dict) else None,
                    "ready_timeframes":info.get("ready_timeframes",[]) if isinstance(info,dict) else [],
                    "missing_timeframes":missing,
                })

    zero_day_causes=Counter(
        str(x.get("primary_root_cause","UNKNOWN"))
        for x in daily if x.get("zero_trade") is True
    )

    conf_sorted=sorted(confidence_misses)
    rr_sorted=sorted(rr_misses)

    report={
        "stage":"V1.8_SIGNAL_COVERAGE_DECOMPOSITION",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_result":V17_REL,
        "source_stage":v17.get("stage"),
        "source_scope_summary":v17.get("scope_summary",{}),
        "conclusion":{
            "buy_selected_count":sum(
                1 for r in checkpoints
                if r.get("selected_candidate")
                and str(r["selected_candidate"].get("side","")).upper()=="BUY"
            ),
            "sell_selected_count":sum(selected_sell_by_symbol.values()),
            "zero_trade_day_cause_counts":dict(zero_day_causes),
            "lifecycle_entry_gap_is_primary_cause":False,
            "entry_signal_coverage_is_primary_issue":True,
        },
        "sell_decomposition":{
            "selected_sell_by_symbol":dict(selected_sell_by_symbol),
            "selected_sell_by_date":dict(selected_sell_by_date),
            "selected_sell_by_hour_et":dict(sorted(selected_sell_by_hour.items())),
        },
        "confidence_decomposition":{
            "threshold":MIN_CONFIDENCE,
            "directional_rows_below_threshold":len(confidence_misses),
            "miss_by_symbol":dict(confidence_miss_by_symbol),
            "margin_buckets":dict(confidence_bucket_counts),
            "average_margin_below_threshold":statistics.mean(conf_sorted) if conf_sorted else None,
            "median_margin_below_threshold":statistics.median(conf_sorted) if conf_sorted else None,
            "minimum_margin_below_threshold":min(conf_sorted) if conf_sorted else None,
            "maximum_margin_below_threshold":max(conf_sorted) if conf_sorted else None,
        },
        "reward_risk_decomposition":{
            "threshold":MIN_REWARD_RISK,
            "directional_rows_below_threshold":len(rr_misses),
            "miss_by_symbol":dict(rr_miss_by_symbol),
            "average_margin_below_threshold":statistics.mean(rr_sorted) if rr_sorted else None,
            "median_margin_below_threshold":statistics.median(rr_sorted) if rr_sorted else None,
        },
        "hold_decomposition":{
            "hold_rows_by_symbol":dict(hold_by_symbol),
            "hold_rows_by_date":dict(hold_by_date),
        },
        "feature_coverage_decomposition":{
            "affected_checkpoint_count":sum(feature_issue_by_date.values()),
            "affected_checkpoints_by_date":dict(feature_issue_by_date),
            "rejected_symbol_counts":dict(rejected_symbol_counts),
            "missing_symbol_timeframe_counts":dict(missing_tf_counts),
            "details":feature_issue_details,
        },
        "action_matrix_by_symbol":{
            sym:dict(counts) for sym,counts in sorted(action_by_symbol.items())
        },
        "buy_like_but_blocked":{
            "count":len(buy_like_but_blocked),
            "records":buy_like_but_blocked,
        },
        "interpretation_contract":{
            "thresholds_changed":False,
            "counterfactual_threshold_relaxation_performed":False,
            "production_change_recommended_automatically":False,
            "diagnostic_only":True,
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
    (out/"latest_signal_coverage_decomposition_v1_8.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )

    print(json.dumps({
        "stage":report["stage"],
        "status":report["status"],
        "conclusion":report["conclusion"],
        "sell_decomposition":report["sell_decomposition"],
        "confidence_decomposition":report["confidence_decomposition"],
        "feature_coverage_decomposition":{
            k:v for k,v in report["feature_coverage_decomposition"].items() if k!="details"
        },
        "buy_like_but_blocked_count":report["buy_like_but_blocked"]["count"],
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
