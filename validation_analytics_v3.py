from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import csv, json, math, random, statistics
from typing import Any

def read_json(p: Path):
    try:
        x=json.loads(p.read_text(encoding="utf-8-sig"))
        return x
    except Exception:
        return None

def read_jsonl(p: Path):
    if not p.exists(): return []
    out=[]
    for raw in p.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip(): continue
        try:
            x=json.loads(raw)
            if isinstance(x,dict): out.append(x)
        except Exception: pass
    return out

def f(v):
    try: return float(v)
    except Exception: return None

def pnl_from(row):
    for k in ("realized_pl","realized_pnl","pnl","profit","net_profit"):
        x=f(row.get(k))
        if x is not None: return x
    return None

def metric(pnls):
    pnls=[x for x in pnls if x is not None]
    if not pnls:
        return {"count":0,"win_rate":None,"expectancy":None,"profit_factor":None,
                "total_pl":0.0,"max_drawdown":0.0,"max_loss_streak":0}
    wins=[x for x in pnls if x>0]
    losses=[x for x in pnls if x<0]
    gp=sum(wins); gl=abs(sum(losses))
    pf=(gp/gl) if gl>0 else ("INF" if gp>0 else None)
    eq=0.0; peak=0.0; dd=0.0; streak=0; maxstreak=0
    for x in pnls:
        eq+=x; peak=max(peak,eq); dd=max(dd,peak-eq)
        if x<0:
            streak+=1; maxstreak=max(maxstreak,streak)
        else:
            streak=0
    return {
        "count":len(pnls),
        "win_rate":round(len(wins)/len(pnls),6),
        "expectancy":round(sum(pnls)/len(pnls),8),
        "profit_factor":round(pf,6) if isinstance(pf,float) else pf,
        "total_pl":round(sum(pnls),8),
        "max_drawdown":round(dd,8),
        "max_loss_streak":maxstreak,
    }

def discover_backtest_rows(root: Path):
    # Conservative discovery: only clearly named backtest result/ledger files.
    candidates=[]
    patterns=[
        "runtime/**/*backtest*.jsonl",
        "runtime/**/*backtest*.json",
        "backtest/**/*result*.jsonl",
        "backtest/**/*result*.json",
        "backtest/**/*trades*.csv",
        "release/**/*backtest*.json",
    ]
    seen=set()
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file() and p not in seen:
                seen.add(p); candidates.append(p)

    rows=[]; used=[]
    for p in candidates:
        try:
            if p.suffix.lower()==".jsonl":
                data=read_jsonl(p)
                extracted=[x for x in data if isinstance(x,dict) and pnl_from(x) is not None]
            elif p.suffix.lower()==".json":
                data=read_json(p)
                extracted=[]
                if isinstance(data,list):
                    extracted=[x for x in data if isinstance(x,dict) and pnl_from(x) is not None]
                elif isinstance(data,dict):
                    for key in ("trades","closed_trades","results","records"):
                        v=data.get(key)
                        if isinstance(v,list):
                            extracted.extend(x for x in v if isinstance(x,dict) and pnl_from(x) is not None)
            elif p.suffix.lower()==".csv":
                with p.open("r",encoding="utf-8-sig",newline="") as h:
                    extracted=[dict(x) for x in csv.DictReader(h)]
                    extracted=[x for x in extracted if pnl_from(x) is not None]
            else:
                extracted=[]
            if extracted:
                used.append(str(p))
                rows.extend(extracted)
        except Exception:
            pass
    return rows, used

def walk_forward_trade_windows(pnls, train=40, test=20):
    if len(pnls)<train+test:
        return {"status":"INSUFFICIENT_DATA","minimum_required":train+test,"available":len(pnls),"windows":[]}
    windows=[]
    start=0
    idx=1
    while start+train+test<=len(pnls):
        tr=pnls[start:start+train]
        te=pnls[start+train:start+train+test]
        windows.append({
            "window":idx,
            "train_range":[start,start+train-1],
            "test_range":[start+train,start+train+test-1],
            "train_metrics":metric(tr),
            "oos_test_metrics":metric(te),
        })
        start+=test
        idx+=1
    return {"status":"PASS","train_size":train,"test_size":test,"windows":windows}

def out_of_sample_split(pnls, ratio=0.7):
    if len(pnls)<20:
        return {"status":"INSUFFICIENT_DATA","available":len(pnls),"minimum_required":20}
    cut=max(1,min(len(pnls)-1,int(len(pnls)*ratio)))
    return {
        "status":"PASS",
        "split_ratio":ratio,
        "in_sample":metric(pnls[:cut]),
        "out_of_sample":metric(pnls[cut:]),
        "in_sample_count":cut,
        "out_of_sample_count":len(pnls)-cut,
    }

def monte_carlo(pnls, simulations=1000, seed=20260807):
    if len(pnls)<20:
        return {"status":"INSUFFICIENT_DATA","available":len(pnls),"minimum_required":20}
    rng=random.Random(seed)
    finals=[]; dds=[]
    n=len(pnls)
    for _ in range(simulations):
        sample=[pnls[rng.randrange(n)] for _ in range(n)]
        m=metric(sample)
        finals.append(m["total_pl"])
        dds.append(m["max_drawdown"])
    finals.sort(); dds.sort()
    def pct(xs,q):
        if not xs:return None
        i=max(0,min(len(xs)-1,int(round((len(xs)-1)*q))))
        return xs[i]
    return {
        "status":"PASS",
        "simulations":simulations,
        "seed":seed,
        "final_pl_p05":pct(finals,.05),
        "final_pl_p50":pct(finals,.50),
        "final_pl_p95":pct(finals,.95),
        "max_drawdown_p50":pct(dds,.50),
        "max_drawdown_p95":pct(dds,.95),
        "probability_positive_final_pl":round(sum(1 for x in finals if x>0)/len(finals),6),
    }

def parameter_result_discovery(root: Path):
    rows=[]
    files=[]
    for pat in ("runtime/**/*parameter*.json","runtime/**/*optimization*.json","backtest/**/*parameter*.json","backtest/**/*optimization*.json"):
        for p in root.glob(pat):
            if not p.is_file(): continue
            data=read_json(p)
            candidates=[]
            if isinstance(data,list): candidates=data
            elif isinstance(data,dict):
                for k in ("results","candidates","parameters","runs"):
                    if isinstance(data.get(k),list):
                        candidates=data[k];break
            clean=[]
            for x in candidates:
                if not isinstance(x,dict): continue
                score=None
                for k in ("score","objective","profit_factor","expectancy","total_return","net_profit"):
                    score=f(x.get(k))
                    if score is not None: break
                if score is not None:
                    y=dict(x);y["_comparison_score"]=score;clean.append(y)
            if clean:
                files.append(str(p));rows.extend(clean)
    rows.sort(key=lambda x:x["_comparison_score"],reverse=True)
    return {
        "status":"PASS" if rows else "NO_DATA",
        "source_files":files,
        "candidate_count":len(rows),
        "top_candidates":rows[:20],
        "automatic_parameter_change":False,
    }

def main_report(root: Path):
    rt=root/"runtime"
    paper_rows=read_jsonl(rt/"paper_full_auto_lifecycle/closed_round_trips.jsonl")
    paper_pnls=[pnl_from(x) for x in paper_rows if pnl_from(x) is not None]

    bt_rows,bt_files=discover_backtest_rows(root)
    bt_pnls=[pnl_from(x) for x in bt_rows if pnl_from(x) is not None]

    paper_metrics=metric(paper_pnls)
    bt_metrics=metric(bt_pnls)

    compare={
        "status":"PASS" if paper_pnls and bt_pnls else "COLLECTING_DATA",
        "paper":paper_metrics,
        "backtest":bt_metrics,
        "paper_trade_count":len(paper_pnls),
        "backtest_trade_count":len(bt_pnls),
        "backtest_source_files":bt_files,
    }
    if paper_pnls and bt_pnls:
        compare["expectancy_gap"]=round((paper_metrics["expectancy"] or 0)-(bt_metrics["expectancy"] or 0),8)
        def pfnum(x):
            if x=="INF": return None
            return f(x)
        pp=pfnum(paper_metrics["profit_factor"]); bp=pfnum(bt_metrics["profit_factor"])
        compare["profit_factor_gap"]=round(pp-bp,6) if pp is not None and bp is not None else None

    report={
        "stage":"PAPER_BACKTEST_VALIDATION_ANALYTICS_V3",
        "status":"PASS",
        "mode":"READ_ONLY_ANALYTICS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "broker_write_performed":False,
        "trading_configuration_changed":False,
        "automatic_parameter_change":False,
        "paper_trade_metrics":paper_metrics,
        "backtest_trade_metrics":bt_metrics,
        "paper_walk_forward":walk_forward_trade_windows(paper_pnls),
        "backtest_walk_forward":walk_forward_trade_windows(bt_pnls),
        "paper_oos":out_of_sample_split(paper_pnls),
        "backtest_oos":out_of_sample_split(bt_pnls),
        "paper_monte_carlo":monte_carlo(paper_pnls),
        "backtest_monte_carlo":monte_carlo(bt_pnls),
        "parameter_evaluation":parameter_result_discovery(root),
        "paper_vs_backtest":compare,
        "interpretation":{
            "walk_forward_scope":"rolling trade-P/L windows; does not retrain or alter strategy parameters",
            "monte_carlo_scope":"bootstrap resampling of observed trade P/L",
            "parameter_scope":"ranks existing optimization artifacts only; does not launch optimization",
            "missing_data_policy":"NO_DATA or INSUFFICIENT_DATA; no fabricated results",
        }
    }
    out=rt/"paper_backtest_validation_analytics_v3"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_validation_analytics.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    return report
