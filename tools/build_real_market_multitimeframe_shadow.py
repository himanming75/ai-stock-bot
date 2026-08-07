from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import argparse, json, math, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from multi_timeframe_ai.engine import analyze_symbol
from paper_autonomous_execution.signals import select_candidate

TIMEFRAMES={
    "1m":1,
    "3m":3,
    "5m":5,
    "15m":15,
    "30m":30,
    "1h":60,
    "1d":390,
}
ALLOWED=("AAPL","MSFT","NVDA","SPY")

def ema(values,span):
    if not values:
        return 0.0
    alpha=2.0/(span+1.0)
    out=float(values[0])
    for v in values[1:]:
        out=alpha*float(v)+(1.0-alpha)*out
    return out

def rsi(values,period=14):
    if len(values)<period+1:
        return 50.0
    gains=[];losses=[]
    for a,b in zip(values[-period-1:-1],values[-period:]):
        d=float(b)-float(a)
        gains.append(max(d,0.0))
        losses.append(max(-d,0.0))
    ag=sum(gains)/period
    al=sum(losses)/period
    if al==0:
        return 100.0 if ag>0 else 50.0
    rs=ag/al
    return 100.0-(100.0/(1.0+rs))

def aggregate(rows,n):
    if not rows:
        return []
    out=[]
    bucket=[]
    for row in rows:
        bucket.append(row)
        if len(bucket)==n:
            out.append({
                "timestamp":bucket[-1]["timestamp"],
                "open":bucket[0]["open"],
                "high":max(x["high"] for x in bucket),
                "low":min(x["low"] for x in bucket),
                "close":bucket[-1]["close"],
                "volume":sum(x["volume"] for x in bucket),
            })
            bucket=[]
    if bucket:
        out.append({
            "timestamp":bucket[-1]["timestamp"],
            "open":bucket[0]["open"],
            "high":max(x["high"] for x in bucket),
            "low":min(x["low"] for x in bucket),
            "close":bucket[-1]["close"],
            "volume":sum(x["volume"] for x in bucket),
        })
    return out

def feature_from_bars(bars, tf):
    closes=[float(x["close"]) for x in bars]
    highs=[float(x["high"]) for x in bars]
    lows=[float(x["low"]) for x in bars]
    vols=[float(x["volume"]) for x in bars]
    if len(closes)<30:
        return None

    c=closes[-1]
    fast=ema(closes[-30:],8)
    slow=ema(closes[-60:],21)
    mom=(c/closes[-6]-1.0) if len(closes)>=6 and closes[-6] else 0.0
    avg_vol=sum(vols[-20:])/max(1,len(vols[-20:]))
    vr=(vols[-1]/avg_vol) if avg_vol else 1.0

    trs=[]
    for i in range(max(1,len(closes)-14),len(closes)):
        prev=closes[i-1]
        tr=max(highs[i]-lows[i],abs(highs[i]-prev),abs(lows[i]-prev))
        trs.append(tr)
    atr=(sum(trs)/len(trs))/c if trs and c else 0.0

    day_gap=0.0
    if tf=="1d" and len(closes)>=2 and bars[-1]["open"]:
        day_gap=float(bars[-1]["open"])/float(closes[-2])-1.0

    rng=max(1e-12,highs[-1]-lows[-1])
    cvr=(c-lows[-1])/rng

    ft=(c/closes[-3]-1.0) if len(closes)>=3 and closes[-3] else 0.0

    return {
        "close":c,
        "ema_fast":fast,
        "ema_slow":slow,
        "momentum":mom,
        "rsi":rsi(closes),
        "volume_ratio":vr,
        "atr_percent":atr,
        "gap_percent":day_gap,
        "close_vs_range":cvr,
        "follow_through":ft,
    }

def load_real_rows(root):
    path=root/"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl"
    if not path.exists():
        raise RuntimeError("Real historical dataset missing")
    by=defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        by[str(r["symbol"]).upper()].append(r)
    for sym in by:
        by[sym].sort(key=lambda x:x["timestamp"])
    return by

def build(root:Path):
    root=Path(root).resolve()
    by=load_real_rows(root)
    analyses=[]
    feature_audit={}

    for symbol in ALLOWED:
        rows=by.get(symbol,[])
        features={}
        tf_meta={}
        for tf,n in TIMEFRAMES.items():
            bars=aggregate(rows,n)
            feat=feature_from_bars(bars,tf)
            if feat is not None:
                features[tf]=feat
                tf_meta[tf]={"aggregated_bars":len(bars)}
        if len(features)!=len(TIMEFRAMES):
            continue
        item=analyze_symbol(symbol,features)
        item["execution_mode"]="ANALYSIS_ONLY"
        analyses.append(item)
        feature_audit[symbol]=tf_meta

    analyses.sort(
        key=lambda x:(
            x.get("confidence_calibration",{}).get("calibrated_confidence",0.0),
            abs(float(x.get("consensus_score",0.0))),
        ),
        reverse=True,
    )

    selected=select_candidate(
        analyses,
        allowed_symbols=ALLOWED,
        min_confidence=0.75,
        min_reward_risk=1.0,
        excluded_symbols=(),
    )

    current_path=root/"release/v11001_12000_multi_timeframe_ai/actual/multi_timeframe_ai_report_bilingual.json"
    current={}
    if current_path.exists():
        try: current=json.loads(current_path.read_text(encoding="utf-8-sig"))
        except Exception: current={}
    current_analyses=current.get("analyses",[]) if isinstance(current,dict) else []
    current_selected=select_candidate(
        current_analyses if isinstance(current_analyses,list) else [],
        allowed_symbols=ALLOWED,
        min_confidence=0.75,
        min_reward_risk=1.0,
        excluded_symbols=(),
    )

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    shadow={
        "stage":"REAL_MARKET_MULTI_TIMEFRAME_SHADOW_ADAPTER_V1",
        "status":"PASS",
        "mode":"SHADOW_ANALYSIS_ONLY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_dataset":"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "source_kind":"REAL_ALPACA_HISTORICAL_1MIN",
        "canonical_engine":"multi_timeframe_ai.engine.analyze_symbol",
        "canonical_selector":"paper_autonomous_execution.signals.select_candidate",
        "allowed_symbols":list(ALLOWED),
        "thresholds":{"min_confidence":0.75,"min_reward_risk":1.0},
        "analyses":analyses,
        "feature_audit":feature_audit,
        "shadow_selected_candidate":selected,
        "current_fixture_selected_candidate":current_selected,
        "selection_matches":selected==current_selected,
        "strategy_equivalence":{
            "same_analyze_symbol_engine":True,
            "same_select_candidate_function":True,
            "same_thresholds":True,
            "same_allowed_symbols":True,
            "same_input_source":False,
            "current_input_source":"OFFLINE_MULTI_TIMEFRAME_FIXTURE",
            "shadow_input_source":"REAL_ALPACA_HISTORICAL_1MIN_AGGREGATED",
            "live_equivalence_asserted":False,
        },
        "contracts":{
            "current_signal_report_modified":False,
            "paper_task_modified":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "strategy_parameter_changed":False,
            "risk_parameter_changed":False,
            "live_auto_enable":False,
        },
    }
    (out/"latest_real_market_shadow.json").write_text(json.dumps(shadow,indent=2,default=str),encoding="utf-8")
    with (out/"real_market_shadow_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps(shadow,default=str)+"\n")
    return shadow

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    print(json.dumps(build(Path(a.root)),indent=2,default=str))
