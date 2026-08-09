
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import math

DIRECTION_KEYS = ("market_regime","regime","trend_regime","market_state","trend_state")
VOLATILITY_KEYS = ("volatility_regime","vol_regime","volatility_state","vol_state")
ID_KEYS = ("trade_id","record_id","position_id","order_id","exit_order_id")

DIRECTION_ALIASES = {
    "BULL":"BULL","BULLISH":"BULL","UPTREND":"BULL","UP_TREND":"BULL","RISK_ON":"BULL",
    "BEAR":"BEAR","BEARISH":"BEAR","DOWNTREND":"BEAR","DOWN_TREND":"BEAR","RISK_OFF":"BEAR",
    "SIDEWAYS":"SIDEWAYS","RANGE":"SIDEWAYS","RANGING":"SIDEWAYS","FLAT":"SIDEWAYS",
    "NEUTRAL":"SIDEWAYS","CHOP":"SIDEWAYS","CHOPPY":"SIDEWAYS",
}
VOLATILITY_ALIASES = {
    "HIGH_VOL":"HIGH_VOL","HIGH_VOLATILITY":"HIGH_VOL","HIGH":"HIGH_VOL","ELEVATED":"HIGH_VOL","VOLATILE":"HIGH_VOL",
    "LOW_VOL":"LOW_VOL","LOW_VOLATILITY":"LOW_VOL","LOW":"LOW_VOL","QUIET":"LOW_VOL","CALM":"LOW_VOL",
    "NORMAL_VOL":"NORMAL_VOL","NORMAL":"NORMAL_VOL","MEDIUM":"NORMAL_VOL","MEDIUM_VOL":"NORMAL_VOL",
}

MIN_GROUP_SAMPLE = 5
MIN_TOTAL_SAMPLE = 10

def _num(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except Exception:
        return None

def _read_jsonl(path: Path, max_rows=10000):
    if not path.exists():
        return []
    try:
        lines=path.read_text(encoding="utf-8",errors="replace").splitlines()[-max_rows:]
    except Exception:
        return []
    rows=[]
    for line in lines:
        if not line.strip():
            continue
        try:
            value=json.loads(line)
        except Exception:
            continue
        if isinstance(value,dict):
            rows.append(value)
    return rows

def _walk_dict(value,prefix=""):
    if not isinstance(value,dict):
        return
    for key,item in value.items():
        path=f"{prefix}.{key}" if prefix else key
        yield path,key,item
        if isinstance(item,dict):
            yield from _walk_dict(item,path)

def _normalize_token(value):
    if value is None:
        return None
    token=str(value).strip().upper().replace("-","_").replace(" ","_")
    return token or None

def _extract_explicit_regime(record):
    direction=None
    volatility=None
    evidence=[]
    for path,key,value in _walk_dict(record):
        key_lower=str(key).lower()
        token=_normalize_token(value)
        if direction is None and key_lower in DIRECTION_KEYS and token in DIRECTION_ALIASES:
            direction=DIRECTION_ALIASES[token]
            evidence.append({"dimension":"direction","path":path,"raw_value":value,"normalized":direction})
        if volatility is None and key_lower in VOLATILITY_KEYS and token in VOLATILITY_ALIASES:
            volatility=VOLATILITY_ALIASES[token]
            evidence.append({"dimension":"volatility","path":path,"raw_value":value,"normalized":volatility})
    return direction,volatility,evidence

def _record_identifiers(record):
    ids=set()
    for _,key,value in _walk_dict(record):
        if str(key).lower() not in ID_KEYS or value is None:
            continue
        token=str(value).strip()
        if token:
            ids.add(token)
    return ids

def _candidate_runtime_files(root: Path):
    runtime=root/"runtime"
    if not runtime.exists():
        return []
    result=[]
    for path in runtime.rglob("*.jsonl"):
        try:
            result.append((path.stat().st_mtime,path))
        except Exception:
            pass
    result.sort(reverse=True)
    return [path for _,path in result[:240]]

def discover_regime_evidence(root: Path,canonical_trades):
    canonical_ids=set()
    trade_by_id={}
    for trade in canonical_trades:
        ids={
            str(trade.get("record_id") or "").strip(),
            str(trade.get("exit_order_id") or "").strip(),
        }
        ids.discard("")
        for identifier in ids:
            canonical_ids.add(identifier)
            trade_by_id[identifier]=trade

    evidence_by_trade_id={}
    source_files=set()
    canonical_raw=root/"runtime"/"paper_full_auto_lifecycle"/"closed_round_trips.jsonl"
    candidate_files=[canonical_raw]
    candidate_files.extend(path for path in _candidate_runtime_files(root) if path!=canonical_raw)

    for path in candidate_files:
        if not path.exists():
            continue
        rel=str(path.relative_to(root)).replace("\\","/")
        for record in _read_jsonl(path):
            identifiers=_record_identifiers(record)
            matched=identifiers.intersection(canonical_ids)
            if not matched:
                continue
            direction,volatility,evidence=_extract_explicit_regime(record)
            if direction is None and volatility is None:
                continue
            source_files.add(rel)
            for identifier in matched:
                trade=trade_by_id.get(identifier)
                canonical_trade_id=str((trade or {}).get("record_id") or identifier)
                slot=evidence_by_trade_id.setdefault(canonical_trade_id,{
                    "direction_regime":None,"volatility_regime":None,"evidence":[]
                })
                if slot["direction_regime"] is None and direction is not None:
                    slot["direction_regime"]=direction
                if slot["volatility_regime"] is None and volatility is not None:
                    slot["volatility_regime"]=volatility
                slot["evidence"].append({"source":rel,"matches":sorted(matched),"fields":evidence})
    return evidence_by_trade_id,sorted(source_files)

def _stats(trades):
    pnls=[_num(t.get("pnl")) for t in trades if _num(t.get("pnl")) is not None]
    wins=[v for v in pnls if v>0]
    losses=[v for v in pnls if v<0]
    gross_profit=sum(wins)
    gross_loss=abs(sum(losses))
    if gross_loss>0:
        pf=gross_profit/gross_loss
    elif gross_profit>0:
        pf="INF"
    else:
        pf=None
    equity=0.0
    peak=0.0
    max_dd=0.0
    for pnl in pnls:
        equity+=pnl
        peak=max(peak,equity)
        max_dd=max(max_dd,peak-equity)
    return {
        "trade_count":len(trades),
        "numeric_trade_count":len(pnls),
        "net_realized_pnl":sum(pnls) if pnls else None,
        "win_rate":len(wins)/len(pnls) if pnls else None,
        "profit_factor":pf,
        "average_trade":sum(pnls)/len(pnls) if pnls else None,
        "max_realized_drawdown":max_dd if pnls else None,
        "sample_status":"PASS_SAMPLE" if len(pnls)>=MIN_GROUP_SAMPLE else ("INSUFFICIENT_SAMPLE" if pnls else "UNOBSERVED"),
    }

def _group_analysis(enriched_trades,field,universe):
    grouped=defaultdict(list)
    for trade in enriched_trades:
        value=trade.get(field)
        if value:
            grouped[value].append(trade)
    rows=[]
    for name in universe:
        rows.append({"name":name,**_stats(grouped.get(name,[]))})
    return rows

def _rank_observed(rows):
    observed=[r for r in rows if r.get("numeric_trade_count",0)>0 and r.get("net_realized_pnl") is not None]
    if not observed:
        return None,None
    ordered=sorted(observed,key=lambda r:r["net_realized_pnl"],reverse=True)
    return ordered[0],ordered[-1]

def build_market_regime_analysis(root: Path,canonical_trades):
    evidence_by_trade_id,source_files=discover_regime_evidence(root,canonical_trades)
    enriched=[]
    observed_direction=0
    observed_volatility=0

    for trade in canonical_trades:
        item=dict(trade)
        trade_id=str(item.get("record_id") or "")
        evidence=evidence_by_trade_id.get(trade_id,{})
        item["direction_regime"]=evidence.get("direction_regime")
        item["volatility_regime"]=evidence.get("volatility_regime")
        item["regime_evidence"]=evidence.get("evidence",[])
        if item["direction_regime"]:
            observed_direction+=1
        if item["volatility_regime"]:
            observed_volatility+=1
        enriched.append(item)

    direction_rows=_group_analysis(enriched,"direction_regime",("BULL","BEAR","SIDEWAYS"))
    volatility_rows=_group_analysis(enriched,"volatility_regime",("HIGH_VOL","NORMAL_VOL","LOW_VOL"))

    best_direction,weakest_direction=_rank_observed(direction_rows)
    best_volatility,weakest_volatility=_rank_observed(volatility_rows)

    total=len(canonical_trades)
    numeric_count=sum(1 for t in canonical_trades if _num(t.get("pnl")) is not None)
    direction_coverage=observed_direction/total if total else 0.0
    volatility_coverage=observed_volatility/total if total else 0.0
    sample_status="PASS_SAMPLE" if numeric_count>=MIN_TOTAL_SAMPLE else "INSUFFICIENT_SAMPLE"
    evidence_status="PASS_EXPLICIT_REGIME_EVIDENCE_FOUND" if (observed_direction or observed_volatility) else "PASS_NO_EXPLICIT_REGIME_EVIDENCE"

    return {
        "stage":"V3.16_MARKET_REGIME_PERFORMANCE_ANALYSIS",
        "status":evidence_status,
        "sample_status":sample_status,
        "canonical_trade_count":total,
        "canonical_numeric_trade_count":numeric_count,
        "minimum_total_sample":MIN_TOTAL_SAMPLE,
        "minimum_group_sample":MIN_GROUP_SAMPLE,
        "coverage":{
            "direction_observed_count":observed_direction,
            "direction_coverage":direction_coverage,
            "volatility_observed_count":observed_volatility,
            "volatility_coverage":volatility_coverage,
        },
        "direction_regimes":direction_rows,
        "volatility_regimes":volatility_rows,
        "best_observed_direction":best_direction,
        "weakest_observed_direction":weakest_direction,
        "best_observed_volatility":best_volatility,
        "weakest_observed_volatility":weakest_volatility,
        "evidence_source_files":source_files,
        "evidence_trade_count":len(evidence_by_trade_id),
        "enriched_trade_preview":list(reversed(enriched[-20:])),
        "interpretation":(
            "No explicit regime evidence is linked to canonical trades; regimes remain UNOBSERVED and are not inferred from price movement."
            if not (observed_direction or observed_volatility)
            else ("Explicit regime evidence exists, but results remain descriptive because the canonical sample is below 10 trades."
                  if sample_status=="INSUFFICIENT_SAMPLE"
                  else "Observed regime results are Paper-validation diagnostics only.")
        ),
        "contracts":{
            "explicit_evidence_only":True,
            "price_based_regime_inference_used":False,
            "unobserved_regimes_fabricated":False,
            "canonical_runtime_files_modified":False,
            "broker_network_used":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "paper_runtime_modified":False,
            "production_parameter_modified":False,
            "production_selector_modified":False,
            "automatic_promotion":False,
            "live_approval":False,
            "duplicate_engine_created":False,
        },
    }
