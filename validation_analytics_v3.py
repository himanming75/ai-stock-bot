from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import csv, json, random

def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return None

def read_jsonl(p: Path):
    if not p.exists():
        return []
    out=[]
    for raw in p.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            x=json.loads(raw)
            if isinstance(x,dict):
                out.append(x)
        except Exception:
            pass
    return out

def f(v):
    try:
        return float(v)
    except Exception:
        return None

def pnl_from(row):
    for k in ("realized_pl","realized_pnl","pnl","profit","net_profit"):
        x=f(row.get(k))
        if x is not None:
            return x
    return None

def metric(pnls):
    pnls=[x for x in pnls if x is not None]
    if not pnls:
        return {"count":0,"win_rate":None,"expectancy":None,"profit_factor":None,
                "total_pl":0.0,"max_drawdown":0.0,"max_loss_streak":0,
                "wins":0,"losses":0,"average_win":None,"average_loss":None}
    wins=[x for x in pnls if x>0]; losses=[x for x in pnls if x<0]
    gp=sum(wins); gl=abs(sum(losses))
    pf=(gp/gl) if gl>0 else ("INF" if gp>0 else None)
    eq=peak=dd=0.0; streak=maxstreak=0
    for x in pnls:
        eq+=x; peak=max(peak,eq); dd=max(dd,peak-eq)
        if x<0: streak+=1; maxstreak=max(maxstreak,streak)
        else: streak=0
    return {"count":len(pnls),"win_rate":round(len(wins)/len(pnls),6),
            "expectancy":round(sum(pnls)/len(pnls),8),
            "profit_factor":round(pf,6) if isinstance(pf,float) else pf,
            "total_pl":round(sum(pnls),8),"max_drawdown":round(dd,8),
            "max_loss_streak":maxstreak,"wins":len(wins),"losses":len(losses),
            "average_win":round(sum(wins)/len(wins),8) if wins else None,
            "average_loss":round(sum(losses)/len(losses),8) if losses else None}

def validation_rows(root: Path):
    rt=root/"runtime"
    rows=read_jsonl(rt/"paper_full_auto_lifecycle/closed_round_trips.jsonl")
    baseline=read_json(rt/"paper_validation_2week_300/baseline.json") or {}
    base=max(0,int(baseline.get("baseline_closed_trade_count",0) or 0))
    return rows[base:], baseline

def time_value(row):
    return row.get("exit_time") or row.get("exit_time_utc") or row.get("closed_at") or row.get("generated_at_utc") or ""

def entry_time_value(row):
    return row.get("entry_time") or row.get("entry_time_utc") or row.get("opened_at") or row.get("created_at") or ""

def parse_dt(value):
    if not value: return None
    try:
        return datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except Exception:
        return None

def parse_hour(value):
    dt=parse_dt(value)
    return dt.hour if dt else None

def group_metrics(rows,key_fn):
    groups=defaultdict(list)
    for r in rows:
        k=key_fn(r); p=pnl_from(r)
        if k not in (None,"") and p is not None: groups[str(k)].append(p)
    out=[]
    for k,pnls in groups.items():
        m=metric(pnls); m["group"]=k; out.append(m)
    out.sort(key=lambda x:(x["count"],x["total_pl"]),reverse=True)
    return out

def confidence_band_value(c):
    c=f(c)
    if c is None: return None
    if c>=.90: return "0.90-1.00"
    if c>=.85: return "0.85-0.90"
    if c>=.80: return "0.80-0.85"
    if c>=.75: return "0.75-0.80"
    return "<0.75"

def confidence_band(row):
    c=f(row.get("confidence"))
    if c is None: c=f((row.get("entry_decision") or {}).get("confidence"))
    return confidence_band_value(c)

def time_bucket(row):
    h=parse_hour(time_value(row))
    if h is None: return None
    if h<14: return "PRE_14_UTC"
    if h<16: return "14-16_UTC"
    if h<18: return "16-18_UTC"
    if h<20: return "18-20_UTC"
    return "20+_UTC"

def discover_backtest_rows(root: Path):
    candidates=[]; seen=set()
    patterns=["runtime/**/*backtest*.jsonl","runtime/**/*backtest*.json",
              "backtest/**/*result*.jsonl","backtest/**/*result*.json",
              "backtest/**/*trades*.csv","release/**/*backtest*.json"]
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file() and p not in seen:
                seen.add(p); candidates.append(p)
    rows=[]; used=[]
    for p in candidates:
        try:
            extracted=[]
            if p.suffix.lower()==".jsonl":
                extracted=[x for x in read_jsonl(p) if pnl_from(x) is not None]
            elif p.suffix.lower()==".json":
                data=read_json(p)
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
            if extracted: used.append(str(p)); rows.extend(extracted)
        except Exception: pass
    return rows,used

def walk_forward_trade_windows(pnls,train=40,test=20):
    if len(pnls)<train+test:
        return {"status":"INSUFFICIENT_DATA","minimum_required":train+test,"available":len(pnls),"windows":[]}
    windows=[]; start=0; idx=1
    while start+train+test<=len(pnls):
        windows.append({"window":idx,"train_metrics":metric(pnls[start:start+train]),
                        "oos_test_metrics":metric(pnls[start+train:start+train+test])})
        start+=test; idx+=1
    return {"status":"PASS","train_size":train,"test_size":test,"windows":windows}

def out_of_sample_split(pnls,ratio=.7):
    if len(pnls)<20: return {"status":"INSUFFICIENT_DATA","available":len(pnls),"minimum_required":20}
    cut=max(1,min(len(pnls)-1,int(len(pnls)*ratio)))
    return {"status":"PASS","split_ratio":ratio,"in_sample":metric(pnls[:cut]),
            "out_of_sample":metric(pnls[cut:]),"in_sample_count":cut,"out_of_sample_count":len(pnls)-cut}

def monte_carlo(pnls,simulations=1000,seed=20260807):
    if len(pnls)<20: return {"status":"INSUFFICIENT_DATA","available":len(pnls),"minimum_required":20}
    rng=random.Random(seed); finals=[]; dds=[]; n=len(pnls)
    for _ in range(simulations):
        m=metric([pnls[rng.randrange(n)] for _ in range(n)])
        finals.append(m["total_pl"]); dds.append(m["max_drawdown"])
    finals.sort(); dds.sort()
    def pct(xs,q): return xs[max(0,min(len(xs)-1,int(round((len(xs)-1)*q))))]
    return {"status":"PASS","simulations":simulations,"seed":seed,
            "final_pl_p05":pct(finals,.05),"final_pl_p50":pct(finals,.50),"final_pl_p95":pct(finals,.95),
            "max_drawdown_p50":pct(dds,.50),"max_drawdown_p95":pct(dds,.95),
            "probability_positive_final_pl":round(sum(1 for x in finals if x>0)/len(finals),6)}

def research_samples(root: Path):
    return read_jsonl(root/"runtime/ai_research_shadow_integration/ai_research_shadow_ledger.jsonl")

def normalized_decision(sample):
    d=sample.get("normalized_decision",{})
    if isinstance(d,dict) and d:
        return d
    # Backward-compatible extraction for earlier research samples.
    modules={x.get("name"):x.get("result",{}) for x in sample.get("module_results",[]) if isinstance(x,dict)}
    ens=modules.get("strategy_ensemble",{}) or {}
    reg=modules.get("market_regime",{}) or {}
    ctx=modules.get("market_context",{}) or {}
    candidate=ens.get("candidate",{}) if isinstance(ens,dict) else {}
    erow=ens.get("ensemble",{}) if isinstance(ens,dict) else {}
    rrow=reg.get("v66_market_regime_classifier",{}) if isinstance(reg,dict) else {}
    crow=ctx.get("market_context_summary",{}) if isinstance(ctx,dict) else {}
    return {"symbol":candidate.get("symbol"),"original_side":candidate.get("side"),
            "candidate_confidence":candidate.get("confidence"),
            "ensemble_decision":erow.get("decision"),"ensemble_weighted_score":erow.get("weighted_score"),
            "market_regime":rrow.get("regime"),"regime_confidence":rrow.get("regime_confidence"),
            "market_entry_context":crow.get("market_entry_context"),"enforced":False,"order_effect":"NONE"}

def link_research_to_closed_trades(root: Path, closed_rows: list[dict], max_age_minutes=120):
    samples=research_samples(root)
    normalized=[]
    for s in samples:
        dt=parse_dt(s.get("generated_at_utc"))
        d=normalized_decision(s)
        if dt and d.get("symbol"):
            normalized.append((dt,d,s))
    normalized.sort(key=lambda x:x[0])

    linked=[]
    for trade in closed_rows:
        symbol=str(trade.get("symbol") or "").upper()
        entry_dt=parse_dt(entry_time_value(trade)) or parse_dt(time_value(trade))
        best=None
        if symbol and entry_dt:
            for sdt,d,s in normalized:
                if str(d.get("symbol") or "").upper()!=symbol: continue
                delta=(entry_dt-sdt).total_seconds()/60
                if 0 <= delta <= max_age_minutes:
                    if best is None or delta < best[0]:
                        best=(delta,sdt,d,s)
        pnl=pnl_from(trade)
        row={"symbol":symbol,"realized_pl":pnl,"trade_entry_time":entry_time_value(trade),
             "trade_exit_time":time_value(trade),"linked":best is not None}
        if best:
            delta,sdt,d,s=best
            row.update({"research_time":sdt.isoformat(),"link_age_minutes":round(delta,3),
                        "original_side":d.get("original_side"),
                        "candidate_confidence":d.get("candidate_confidence"),
                        "confidence_band":confidence_band_value(d.get("candidate_confidence")),
                        "ensemble_decision":d.get("ensemble_decision"),
                        "ensemble_weighted_score":d.get("ensemble_weighted_score"),
                        "market_regime":d.get("market_regime"),
                        "market_entry_context":d.get("market_entry_context")})
        linked.append(row)
    return linked

def linked_group_metrics(rows,key):
    usable=[r for r in rows if r.get("linked") and r.get(key) not in (None,"") and r.get("realized_pl") is not None]
    return group_metrics(usable,lambda r:r.get(key))

def ai_decision_outcome_metrics(linked):
    usable=[r for r in linked if r.get("linked") and r.get("realized_pl") is not None]
    ens=linked_group_metrics(usable,"ensemble_decision")
    reg=linked_group_metrics(usable,"market_regime")
    conf=linked_group_metrics(usable,"confidence_band")
    ctx=linked_group_metrics(usable,"market_entry_context")

    skip=[r for r in usable if str(r.get("ensemble_decision") or "").upper() in {"SKIP","SKIP_OBSERVATION","AVOID","WAIT"}]
    allow=[r for r in usable if r not in skip]
    return {
        "status":"PASS" if usable else "COLLECTING_DATA",
        "linked_trade_count":len(usable),
        "link_rate":round(len(usable)/len(linked),6) if linked else None,
        "ensemble_performance":ens,
        "regime_performance":reg,
        "confidence_calibration":conf,
        "market_context_performance":ctx,
        "ai_skip_actual_trade_metrics":metric([r["realized_pl"] for r in skip]),
        "ai_allow_actual_trade_metrics":metric([r["realized_pl"] for r in allow]),
        "interpretation":"If AI_SKIP trades lose money more often than AI_ALLOW trades, shadow AI may be adding filtering value. Advisory only.",
    }

def research_opportunity_summary(root: Path):
    samples=research_samples(root)
    rows=[]
    for s in samples:
        d=normalized_decision(s)
        if not d.get("symbol"): continue
        rows.append({"time":s.get("generated_at_utc"),**d})
    freq=defaultdict(int); regimes=defaultdict(int); decisions=defaultdict(int)
    for r in rows:
        freq[str(r.get("symbol"))]+=1
        regimes[str(r.get("market_regime"))]+=1
        decisions[str(r.get("ensemble_decision"))]+=1
    return {"sample_count":len(rows),
            "symbol_frequency":[{"group":k,"count":v} for k,v in sorted(freq.items(),key=lambda x:x[1],reverse=True)],
            "regime_frequency":[{"group":k,"count":v} for k,v in sorted(regimes.items(),key=lambda x:x[1],reverse=True)],
            "ensemble_decision_frequency":[{"group":k,"count":v} for k,v in sorted(decisions.items(),key=lambda x:x[1],reverse=True)]}

def live_readiness(root: Path, paper_metrics: dict, rows: list[dict], baseline: dict, ai_metrics: dict):
    reliability=read_json(root/"runtime/paper_operational_reliability_v2/latest_operational_reliability_report.json") or {}
    health=reliability.get("health",{}) if isinstance(reliability,dict) else {}
    health_score=f(health.get("score")); issues=health.get("issues",[]) if isinstance(health,dict) else []
    dates={str(time_value(r))[:10] for r in rows if time_value(r)}
    pf=paper_metrics.get("profit_factor")
    pf_ok=(pf=="INF") or (isinstance(pf,(int,float)) and pf>=1.2)
    exp=paper_metrics.get("expectancy")
    checks={"closed_trades_300":len(rows)>=300,"trading_days_10":len(dates)>=10,
            "profit_factor_at_least_1_20":bool(pf_ok),
            "expectancy_positive":isinstance(exp,(int,float)) and exp>0,
            "operational_health_at_least_95":health_score is not None and health_score>=95,
            "zero_unresolved_operational_issues":len(issues)==0,
            "ai_outcome_links_available":ai_metrics.get("linked_trade_count",0)>=20,
            "live_auto_enable_off":True}
    # AI link is advisory for eligibility so lack of links cannot auto-block the financial gate.
    core_keys=[k for k in checks if k!="ai_outcome_links_available"]
    eligible=all(checks[k] for k in core_keys)
    return {"status":"ELIGIBLE_FOR_LIVE_STAGE_1" if eligible else "NOT_READY","eligible":eligible,
            "checks":checks,"observed_closed_trades":len(rows),"observed_trading_days":len(dates),
            "profit_factor":pf,"expectancy":exp,"operational_health_score":health_score,
            "operational_issues":issues,"ai_linked_trade_count":ai_metrics.get("linked_trade_count",0),
            "automatic_live_enable":False,"policy":"ADVISORY_ONLY"}

def main_report(root: Path):
    root=Path(root); rt=root/"runtime"
    paper_rows,baseline=validation_rows(root)
    paper_pnls=[pnl_from(x) for x in paper_rows if pnl_from(x) is not None]
    bt_rows,bt_files=discover_backtest_rows(root); bt_pnls=[pnl_from(x) for x in bt_rows if pnl_from(x) is not None]
    pm=metric(paper_pnls); bm=metric(bt_pnls)
    linked=link_research_to_closed_trades(root,paper_rows)
    ai_metrics=ai_decision_outcome_metrics(linked)
    compare={"status":"PASS" if paper_pnls and bt_pnls else "COLLECTING_DATA","paper":pm,"backtest":bm,
             "paper_trade_count":len(paper_pnls),"backtest_trade_count":len(bt_pnls),"backtest_source_files":bt_files}
    if paper_pnls and bt_pnls:
        compare["expectancy_gap"]=round((pm["expectancy"] or 0)-(bm["expectancy"] or 0),8)

    report={"stage":"PAPER_BACKTEST_VALIDATION_ANALYTICS_V3","status":"PASS","mode":"READ_ONLY_ANALYTICS",
            "generated_at_utc":datetime.now(timezone.utc).isoformat(),"broker_write_performed":False,
            "trading_configuration_changed":False,"automatic_parameter_change":False,
            "validation_baseline":baseline,"paper_trade_metrics":pm,"backtest_trade_metrics":bm,
            "symbol_breakdown":group_metrics(paper_rows,lambda r:r.get("symbol")),
            "exit_reason_breakdown":group_metrics(paper_rows,lambda r:r.get("exit_reason") or r.get("reason")),
            "time_bucket_breakdown":group_metrics(paper_rows,time_bucket),
            "confidence_breakdown":group_metrics(paper_rows,confidence_band),
            "paper_walk_forward":walk_forward_trade_windows(paper_pnls),
            "backtest_walk_forward":walk_forward_trade_windows(bt_pnls),
            "paper_oos":out_of_sample_split(paper_pnls),"backtest_oos":out_of_sample_split(bt_pnls),
            "paper_monte_carlo":monte_carlo(paper_pnls),"backtest_monte_carlo":monte_carlo(bt_pnls),
            "paper_vs_backtest":compare,
            "ai_research_samples":research_opportunity_summary(root),
            "ai_outcome_linkage":{"rows":linked[-100:],"metrics":ai_metrics},
            "live_readiness":live_readiness(root,pm,paper_rows,baseline,ai_metrics),
            "interpretation":{"scope":"read-only validation intelligence; no broker/order/strategy mutation",
                              "ai_link_scope":"nearest prior same-symbol research sample within 120 minutes; advisory only",
                              "live_readiness_scope":"advisory only; never enables live trading"}}
    out=rt/"paper_backtest_validation_analytics_v3"; out.mkdir(parents=True,exist_ok=True)
    (out/"latest_validation_analytics.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    return report
