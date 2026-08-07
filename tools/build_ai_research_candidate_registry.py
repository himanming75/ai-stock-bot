from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import validation_analytics_v3 as analytics

def read_json(path: Path):
    try:
        x=json.loads(path.read_text(encoding="utf-8-sig"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None

def metric_score(row):
    n=int(row.get("count",0) or 0)
    exp=safe_float(row.get("expectancy"))
    wr=safe_float(row.get("win_rate"))
    pf=row.get("profit_factor")
    pfv=10.0 if pf=="INF" else safe_float(pf)
    if n<10 or exp is None:
        return None
    score=0.0
    score += min(3.0,max(-3.0,exp))*20.0
    if wr is not None:
        score += (wr-.5)*40.0
    if pfv is not None:
        score += min(3.0,max(0.0,pfv-1.0))*10.0
    score += min(20.0,n/5.0)
    return round(score,4)

def candidate_rows(report):
    sources=[
        ("SYMBOL",report.get("symbol_breakdown",[])),
        ("EXIT_REASON",report.get("exit_reason_breakdown",[])),
        ("TIME_BUCKET",report.get("time_bucket_breakdown",[])),
        ("CONFIDENCE_BAND",report.get("confidence_breakdown",[])),
    ]
    matrix=report.get("regime_decision_outcome_matrix",[]) or []
    out=[]
    for source,rows in sources:
        for r in rows or []:
            score=metric_score(r)
            if score is None: continue
            out.append({
                "candidate_type":source,
                "key":str(r.get("group","")),
                "sample_count":int(r.get("count",0) or 0),
                "win_rate":r.get("win_rate"),
                "expectancy":r.get("expectancy"),
                "profit_factor":r.get("profit_factor"),
                "total_pl":r.get("total_pl"),
                "research_score":score,
            })
    for r in matrix:
        rr=dict(r)
        rr["group"]=f"{r.get('market_regime','UNKNOWN')}::{r.get('ensemble_decision','UNKNOWN')}"
        score=metric_score(rr)
        if score is None: continue
        out.append({
            "candidate_type":"REGIME_X_AI_DECISION",
            "key":rr["group"],
            "sample_count":int(r.get("count",0) or 0),
            "win_rate":r.get("win_rate"),
            "expectancy":r.get("expectancy"),
            "profit_factor":r.get("profit_factor"),
            "total_pl":r.get("total_pl"),
            "research_score":score,
        })
    out.sort(key=lambda x:(x["research_score"],x["sample_count"]),reverse=True)
    return out

def classify_candidate(row):
    s=row["research_score"]
    if s>=30:
        return "PROMISING_RESEARCH_ONLY"
    if s<=-10:
        return "NEGATIVE_RESEARCH_ONLY"
    return "NEUTRAL_RESEARCH_ONLY"

def run_existing_counterfactual(root: Path):
    runner=root/"tools/run_shadow_counterfactual_v76_v80.py"
    if not runner.exists():
        return {"status":"NOT_PRESENT","executed":False}
    try:
        p=subprocess.run(
            [sys.executable,str(runner),"--repository-root",str(root)],
            cwd=str(root),capture_output=True,text=True,
            encoding="utf-8",errors="replace",timeout=120
        )
        return {
            "status":"PASS" if p.returncode==0 else "ADVISORY_FAIL",
            "executed":True,
            "exit_code":p.returncode,
            "tail":"\n".join(((p.stdout or "")+"\n"+(p.stderr or "")).splitlines()[-30:]),
        }
    except Exception as exc:
        return {"status":"ADVISORY_ERROR","executed":True,
                "error":f"{type(exc).__name__}: {exc}"}

def promotion_gate(report):
    rr=report.get("research_readiness_scorecard",{}) or {}
    wf=report.get("paper_walk_forward_stability",{}) or {}
    oos=report.get("paper_oos_degradation",{}) or {}
    mc=report.get("paper_monte_carlo",{}) or {}
    boot=report.get("paper_bootstrap_expectancy",{}) or {}
    wilson=report.get("paper_win_rate_wilson_95",{}) or {}
    pm=report.get("paper_trade_metrics",{}) or {}
    trades=int(pm.get("count",0) or 0)
    dates=report.get("live_readiness",{}).get("observed_trading_days",0) if isinstance(report.get("live_readiness"),dict) else 0
    checks={
        "closed_trades_300":trades>=300,
        "trading_days_10":int(dates or 0)>=10,
        "walk_forward_stable":wf.get("stable") is True,
        "oos_positive":oos.get("oos_positive") is True,
        "monte_carlo_positive_ge_60pct":
            safe_float(mc.get("probability_positive_final_pl")) is not None
            and safe_float(mc.get("probability_positive_final_pl"))>=.60,
        "bootstrap_positive_ge_60pct":
            safe_float(boot.get("probability_positive_expectancy")) is not None
            and safe_float(boot.get("probability_positive_expectancy"))>=.60,
        "wilson_lower_bound_available":wilson.get("low") is not None,
        "research_readiness_scorecard_ready":rr.get("status")=="RESEARCH_READY",
    }
    passed=sum(1 for v in checks.values() if v)
    return {
        "status":"RESEARCH_PROMOTION_REVIEW_READY" if all(checks.values()) else "COLLECTING_DATA",
        "checks":checks,
        "passed_checks":passed,
        "total_checks":len(checks),
        "manual_review_required":True,
        "automatic_strategy_promotion":False,
        "automatic_parameter_change":False,
        "automatic_risk_change":False,
        "order_path_effect":"NONE",
    }

def build(root: Path):
    root=Path(root)
    report=analytics.main_report(root)
    rows=candidate_rows(report)
    for r in rows:
        r["classification"]=classify_candidate(r)

    gate=promotion_gate(report)
    counterfactual=run_existing_counterfactual(root)

    result={
        "stage":"AI_RESEARCH_PROMOTION_GATE_V1",
        "status":"PASS",
        "mode":"RESEARCH_ONLY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "candidate_count":len(rows),
        "top_candidates":rows[:25],
        "negative_candidates":[x for x in rows if x["classification"]=="NEGATIVE_RESEARCH_ONLY"][:25],
        "promotion_gate":gate,
        "existing_shadow_counterfactual":counterfactual,
        "source_summary":{
            "paper_trade_count":(report.get("paper_trade_metrics") or {}).get("count",0),
            "linked_ai_trade_count":((report.get("ai_outcome_linkage") or {}).get("metrics") or {}).get("linked_trade_count",0),
            "data_sufficiency":((report.get("research_readiness_scorecard") or {}).get("data_sufficiency") or {}),
            "robustness_status":(report.get("research_readiness_scorecard") or {}).get("status","COLLECTING_DATA"),
        },
        "contracts":{
            "broker_write_performed":False,
            "order_submission_performed":False,
            "strategy_parameter_changed":False,
            "risk_parameter_changed":False,
            "paper_decision_path_changed":False,
            "live_decision_path_changed":False,
            "automatic_promotion":False,
            "live_auto_enable":False,
        },
    }

    out=root/"runtime/ai_research_promotion_gate"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_research_promotion_gate.json").write_text(
        json.dumps(result,indent=2,default=str),encoding="utf-8"
    )
    with (out/"research_promotion_gate_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps(result,default=str)+"\n")
    return result

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\stock-bot")
    args=ap.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
