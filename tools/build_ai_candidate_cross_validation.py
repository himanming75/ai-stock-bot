from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

import validation_analytics_v3 as a
from tools.build_ai_research_candidate_registry import build as build_registry

def safe_float(v):
    try: return float(v)
    except Exception: return None

def pf_num(v):
    if v=="INF": return 999.0
    return safe_float(v)

def rows_for_candidate(rows,ctype,key):
    if ctype=="SYMBOL":
        return [r for r in rows if str(r.get("symbol",""))==key]
    if ctype=="EXIT_REASON":
        return [r for r in rows if str(r.get("exit_reason") or r.get("reason") or "")==key]
    if ctype=="TIME_BUCKET":
        return [r for r in rows if str(a.time_bucket(r) or "")==key]
    if ctype=="CONFIDENCE_BAND":
        return [r for r in rows if str(a.confidence_band(r) or "")==key]
    return []

def metrics_for(rows):
    return a.metric([a.pnl_from(r) for r in rows if a.pnl_from(r) is not None])

def compare_metrics(paper,backtest):
    pc=int(paper.get("count",0) or 0)
    bc=int(backtest.get("count",0) or 0)
    pe=safe_float(paper.get("expectancy"))
    be=safe_float(backtest.get("expectancy"))
    pw=safe_float(paper.get("win_rate"))
    bw=safe_float(backtest.get("win_rate"))
    pp=pf_num(paper.get("profit_factor"))
    bp=pf_num(backtest.get("profit_factor"))

    if pc<10 or bc<20:
        return {
            "status":"INSUFFICIENT_DATA",
            "paper_minimum":10,
            "backtest_minimum":20,
            "paper_count":pc,
            "backtest_count":bc,
        }

    same_expectancy_sign=(pe is not None and be is not None and ((pe>0 and be>0) or (pe<0 and be<0) or (pe==0 and be==0)))
    win_rate_gap=abs(pw-bw) if pw is not None and bw is not None else None
    expectancy_gap=abs(pe-be) if pe is not None and be is not None else None

    pf_same_quality=None
    if pp is not None and bp is not None:
        pf_same_quality=(pp>=1.0)==(bp>=1.0)

    checks={
        "expectancy_direction_matches":same_expectancy_sign,
        "win_rate_gap_le_15pct":win_rate_gap is not None and win_rate_gap<=0.15,
        "profit_factor_quality_matches":pf_same_quality is True,
    }
    passed=sum(1 for x in checks.values() if x)
    if passed==3:
        status="CROSS_VALIDATED_RESEARCH_ONLY"
    elif passed<=1:
        status="DIVERGENT_RESEARCH_ONLY"
    else:
        status="MIXED_RESEARCH_ONLY"

    return {
        "status":status,
        "checks":checks,
        "passed_checks":passed,
        "total_checks":3,
        "win_rate_gap":round(win_rate_gap,6) if win_rate_gap is not None else None,
        "expectancy_gap":round(expectancy_gap,8) if expectancy_gap is not None else None,
        "paper_count":pc,
        "backtest_count":bc,
    }

def build(root: Path):
    root=Path(root)
    analytics=a.main_report(root)
    registry=build_registry(root)
    paper_rows,_=a.validation_rows(root)
    backtest_rows,backtest_files=a.discover_backtest_rows(root)

    source_candidates=(registry.get("top_candidates",[]) or [])+(registry.get("negative_candidates",[]) or [])
    dedup={}
    for c in source_candidates:
        dedup[(c.get("candidate_type"),c.get("key"))]=c

    results=[]
    for (_, _),c in dedup.items():
        ctype=str(c.get("candidate_type") or "")
        key=str(c.get("key") or "")

        if ctype=="REGIME_X_AI_DECISION":
            results.append({
                "candidate_type":ctype,
                "key":key,
                "research_classification":c.get("classification"),
                "research_score":c.get("research_score"),
                "status":"PAPER_ONLY_NOT_BACKTEST_COMPARABLE",
                "reason":"Backtest rows do not have a canonical regime x AI-decision annotation contract.",
                "automatic_action":"NONE",
            })
            continue

        prows=rows_for_candidate(paper_rows,ctype,key)
        brows=rows_for_candidate(backtest_rows,ctype,key)
        pm=metrics_for(prows)
        bm=metrics_for(brows)
        comp=compare_metrics(pm,bm)

        results.append({
            "candidate_type":ctype,
            "key":key,
            "research_classification":c.get("classification"),
            "research_score":c.get("research_score"),
            "paper_metrics":pm,
            "backtest_metrics":bm,
            "cross_validation":comp,
            "status":comp.get("status"),
            "automatic_action":"NONE",
        })

    counts={}
    for r in results:
        k=r.get("status","UNKNOWN")
        counts[k]=counts.get(k,0)+1

    wf_p=analytics.get("paper_walk_forward_stability",{}) or {}
    wf_b=a.walk_forward_stability(analytics.get("backtest_walk_forward",{}) or {})
    oos_p=analytics.get("paper_oos_degradation",{}) or {}
    oos_b=a.oos_degradation(analytics.get("backtest_oos",{}) or {})

    portfolio_checks={
        "paper_walk_forward_stable":wf_p.get("stable") is True,
        "backtest_walk_forward_stable":wf_b.get("stable") is True,
        "paper_oos_positive":oos_p.get("oos_positive") is True,
        "backtest_oos_positive":oos_b.get("oos_positive") is True,
        "paper_closed_trades_300":int((analytics.get("paper_trade_metrics") or {}).get("count",0) or 0)>=300,
        "backtest_trades_60":int((analytics.get("backtest_trade_metrics") or {}).get("count",0) or 0)>=60,
    }

    result={
        "stage":"AI_CANDIDATE_PAPER_BACKTEST_CROSS_VALIDATION_V1",
        "status":"PASS",
        "mode":"RESEARCH_ONLY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "candidate_count":len(results),
        "candidate_results":results,
        "status_counts":counts,
        "portfolio_cross_validation":{
            "status":"REVIEW_READY" if all(portfolio_checks.values()) else "COLLECTING_DATA",
            "checks":portfolio_checks,
            "passed_checks":sum(1 for x in portfolio_checks.values() if x),
            "total_checks":len(portfolio_checks),
            "manual_review_required":True,
        },
        "data_sources":{
            "paper_trade_count":len(paper_rows),
            "backtest_trade_count":len(backtest_rows),
            "backtest_source_files":backtest_files,
            "registry_candidate_count":registry.get("candidate_count",0),
        },
        "contracts":{
            "broker_write_performed":False,
            "order_submission_performed":False,
            "task_change_performed":False,
            "strategy_parameter_changed":False,
            "risk_parameter_changed":False,
            "paper_decision_path_changed":False,
            "live_decision_path_changed":False,
            "automatic_candidate_promotion":False,
            "automatic_candidate_rejection":False,
            "live_auto_enable":False,
        },
    }

    out=root/"runtime/ai_candidate_cross_validation"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_ai_candidate_cross_validation.json").write_text(
        json.dumps(result,indent=2,default=str),encoding="utf-8"
    )
    with (out/"ai_candidate_cross_validation_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps(result,default=str)+"\n")
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    args=p.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
