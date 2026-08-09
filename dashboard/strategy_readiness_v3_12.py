
from __future__ import annotations
import math

MIN_READY_TRADES = 20
MIN_EVALUATE_TRADES = 10

def _num(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except Exception:
        return None

def _clamp(value, low=0.0, high=100.0):
    return max(low,min(high,float(value)))

def _sample_score(count):
    return _clamp((count/MIN_READY_TRADES)*100.0)

def _profitability_score(h):
    win=_num(h.get("win_rate")) or 0.0
    avg=_num(h.get("average_trade"))
    pf=h.get("profit_factor")
    if pf=="INF":
        pf_score=100.0
    else:
        pfn=_num(pf)
        pf_score=0.0 if pfn is None else _clamp((pfn/2.0)*100.0)
    win_score=_clamp(win*100.0)
    avg_score=100.0 if avg is not None and avg>0 else 0.0
    return round(pf_score*0.45+win_score*0.40+avg_score*0.15,2)

def _risk_score(h,d):
    dd=_num(h.get("max_realized_drawdown"))
    net=_num(h.get("net_realized_pnl"))
    loss_streak=_num((d.get("streaks") or {}).get("max_consecutive_losses")) or 0.0
    if dd is None:
        dd_score=0.0
    elif dd==0:
        dd_score=100.0
    else:
        base=abs(net) if net not in (None,0) else 1.0
        dd_score=_clamp(100.0-(dd/base)*100.0)
    streak_score=_clamp(100.0-loss_streak*15.0)
    return round(dd_score*0.70+streak_score*0.30,2)

def _consistency_score(d):
    rows=[r for r in (d.get("by_date") or []) if _num(r.get("net_realized_pnl")) is not None]
    if not rows:
        return 0.0
    positive=sum(1 for r in rows if _num(r.get("net_realized_pnl"))>0)
    ratio=positive/len(rows)
    wins=_num((d.get("streaks") or {}).get("max_consecutive_wins")) or 0.0
    losses=_num((d.get("streaks") or {}).get("max_consecutive_losses")) or 0.0
    balance=_clamp(50.0+(wins-losses)*10.0)
    return round(ratio*100.0*0.70+balance*0.30,2)

def _diversification_score(d):
    symbols=len(d.get("by_symbol") or [])
    reasons=len(d.get("by_exit_reason") or [])
    symbol_score=_clamp((symbols/3.0)*100.0)
    reason_score=_clamp((reasons/3.0)*100.0)
    return round(symbol_score*0.70+reason_score*0.30,2)

def build_strategy_readiness(trade_analytics):
    h=trade_analytics.get("historical") or {}
    d=trade_analytics.get("performance_diagnostics") or {}
    count=int(h.get("numeric_trade_count") or 0)

    sample=round(_sample_score(count),2)
    profitability=_profitability_score(h)
    risk=_risk_score(h,d)
    consistency=_consistency_score(d)
    diversification=_diversification_score(d)

    raw=round(sample*0.35+profitability*0.25+risk*0.20+consistency*0.15+diversification*0.05,2)

    if count<MIN_EVALUATE_TRADES:
        status="NOT_READY"
        overall=min(raw,49.0)
    elif count<MIN_READY_TRADES:
        status="EVALUATING"
        overall=min(raw,69.0)
    elif raw>=80:
        status="READY_FOR_EXTENDED_PAPER"
        overall=raw
    elif raw>=65:
        status="CONDITIONAL"
        overall=raw
    else:
        status="NOT_READY"
        overall=raw

    blockers=[]
    if count<MIN_READY_TRADES:
        blockers.append(f"Canonical numeric trade sample {count}/{MIN_READY_TRADES}")
    if d.get("status")=="INSUFFICIENT_SAMPLE":
        blockers.append("Performance diagnostics sample is insufficient")
    if len(d.get("by_symbol") or [])<2:
        blockers.append("Insufficient symbol diversification")
    if int(d.get("loss_count") or 0)==0:
        blockers.append("No losing canonical trades observed yet")

    interpretation={
        "NOT_READY":"More canonical Paper evidence is required.",
        "EVALUATING":"Evidence is accumulating but is not yet sufficient for readiness.",
        "CONDITIONAL":"Sample is adequate but quality metrics need improvement.",
        "READY_FOR_EXTENDED_PAPER":"Metrics support extended Paper validation only; this is not Live approval.",
    }.get(status)

    return {
        "stage":"V3.12_STRATEGY_QUALITY_READINESS_SCORE",
        "status":status,
        "overall_score":round(overall,2),
        "raw_overall_score":raw,
        "scores":{
            "sample_confidence":sample,
            "profitability_quality":profitability,
            "risk_quality":risk,
            "consistency":consistency,
            "diversification":diversification,
        },
        "thresholds":{
            "minimum_evaluation_trades":MIN_EVALUATE_TRADES,
            "minimum_ready_trades":MIN_READY_TRADES,
            "ready_score":80,
            "conditional_score":65,
        },
        "canonical_numeric_trade_count":count,
        "blockers":blockers,
        "interpretation":interpretation,
        "contracts":{
            "advisory_only":True,
            "automatic_promotion":False,
            "live_approval":False,
            "broker_network_used":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "paper_runtime_modified":False,
            "production_parameter_modified":False,
            "production_selector_modified":False,
            "duplicate_engine_created":False,
        },
    }
