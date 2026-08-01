from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

def cj(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class SignalConfig:
    macd_weight:float=1.0
    roc_weight:float=1.0
    stochastic_weight:float=1.0
    bollinger_weight:float=1.0
    buy_threshold:float=1.5
    sell_threshold:float=-1.5
    stochastic_oversold:float=25.0
    stochastic_overbought:float=75.0
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if not self.buy_threshold>0 or not self.sell_threshold<0: raise ValueError("thresholds")
        if not 0<=self.stochastic_oversold<self.stochastic_overbought<=100: raise ValueError("stochastic bounds")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def validate_indicator_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text()); u=dict(c); e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V79.70" or c.get("status")!="PASS": raise ValueError("bad indicator certificate")
    return c

def locate_indicator_data(output:Path,cert:dict[str,Any])->Path:
    cid=cert["indicator_summary"]["cache_id"]
    p=output/"cache"/cid/"historical_indicators.jsonl"
    if not p.is_file(): raise FileNotFoundError(p)
    return p

def load_indicator_rows(path:Path)->list[dict[str,Any]]:
    out=[]
    for n,line in enumerate(path.read_text().splitlines(),1):
        if not line.strip(): continue
        try: x=json.loads(line)
        except Exception as e: raise ValueError(f"bad line {n}") from e
        if not {"symbol","timeframe","timestamp","source_close","indicators"}.issubset(x): raise ValueError("missing fields")
        out.append(x)
    if not out: raise ValueError("empty indicator input")
    return out

def build_signal_registry(c:SignalConfig)->dict[str,Any]:
    c.validate()
    rules=[
        {"name":"macd_direction","description":"MACD above/below signal"},
        {"name":"roc_momentum","description":"ROC positive/negative"},
        {"name":"stochastic_extreme","description":"oversold/overbought"},
        {"name":"bollinger_position","description":"price below lower/above upper band"},
    ]
    d={"stage":"V79.71","rule_count":len(rules),"rules":rules,
       "actions":["BUY","SELL","HOLD"],"buy_threshold":c.buy_threshold,"sell_threshold":c.sell_threshold}
    d["registry_sha256"]=hj(d); return d

def build_signals(rows:list[dict[str,Any]],c:SignalConfig)->list[dict[str,Any]]:
    c.validate(); out=[]
    for x in rows:
        i=x["indicators"]; score=0.0; reasons=[]
        macd=i.get("macd"); sig=i.get("macd_signal")
        if macd is not None and sig is not None:
            if macd>sig: score+=c.macd_weight; reasons.append("MACD_BULLISH")
            elif macd<sig: score-=c.macd_weight; reasons.append("MACD_BEARISH")
        roc=i.get("roc")
        if roc is not None:
            if roc>0: score+=c.roc_weight; reasons.append("ROC_POSITIVE")
            elif roc<0: score-=c.roc_weight; reasons.append("ROC_NEGATIVE")
        st=i.get("stochastic_k")
        if st is not None:
            if st<=c.stochastic_oversold: score+=c.stochastic_weight; reasons.append("STOCHASTIC_OVERSOLD")
            elif st>=c.stochastic_overbought: score-=c.stochastic_weight; reasons.append("STOCHASTIC_OVERBOUGHT")
        close=float(x["source_close"]); lo=i.get("bollinger_lower"); hi=i.get("bollinger_upper")
        if lo is not None and close<lo: score+=c.bollinger_weight; reasons.append("BELOW_LOWER_BAND")
        elif hi is not None and close>hi: score-=c.bollinger_weight; reasons.append("ABOVE_UPPER_BAND")
        action="BUY" if score>=c.buy_threshold else ("SELL" if score<=c.sell_threshold else "HOLD")
        confidence=min(1.0,abs(score)/(abs(c.buy_threshold)+abs(c.sell_threshold)))
        out.append({"symbol":x["symbol"],"timeframe":x["timeframe"],"timestamp":x["timestamp"],
                    "source_close":close,"signal":action,"score":score,"confidence":confidence,"reasons":reasons})
    return sorted(out,key=lambda x:(x["symbol"],x["timestamp"]))

def validate_signal_rows(rows):
    keys=set(); counts={"BUY":0,"SELL":0,"HOLD":0}
    for x in rows:
        k=(x["symbol"],x["timeframe"],x["timestamp"])
        if k in keys: raise ValueError("duplicate signal key")
        keys.add(k)
        if x["signal"] not in counts: raise ValueError("invalid signal")
        if not math.isfinite(float(x["score"])) or not 0<=float(x["confidence"])<=1: raise ValueError("invalid score")
        counts[x["signal"]]+=1
    return {"signal_row_count":len(rows),"unique_signal_key_count":len(keys),
            "buy_count":counts["BUY"],"sell_count":counts["SELL"],"hold_count":counts["HOLD"]}

def store_signals(out:Path,src:Path,reg,rows,stats):
    data="".join(json.dumps(x,sort_keys=True)+"\n" for x in rows).encode()
    cid=f"signals-{hb(src.read_bytes())[:16]}-{reg['registry_sha256'][:12]}"
    dp=out/"cache"/cid/"historical_signals.jsonl"
    created=not dp.exists()
    if dp.exists() and dp.read_bytes()!=data: raise ValueError("signal cache conflict")
    if created: aw(dp,data)
    rp=out/"signal_rule_registry.json"; wj(rp,reg)
    led={"stage":"V79.73","cache_id":cid,"created":created,"reused_existing_cache":not created,**stats}
    led["ledger_sha256"]=hj(led); lp=out/"signal_cache_ledger.json"; wj(lp,led)
    man={"stage":"V79.74","cache_id":cid,"rule_count":reg["rule_count"],**stats,"files":{},
         "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    for n,p in (("registry",rp),("ledger",lp),("signals",dp)):
        b=p.read_bytes(); man["files"][n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    man["manifest_sha256"]=hj(man); wj(out/"historical_signal_manifest_v79_74.json",man)
    return {"cache_id":cid,"created":created,"reused_existing_cache":not created,"manifest":man}

def verify_signal_manifest(out:Path,man):
    u=dict(man); e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for info in man["files"].values():
        p=out/info["relative_path"]; b=p.read_bytes()
        if hb(b)!=info["sha256"] or len(b)!=info["byte_size"]: raise ValueError("tamper")
    return True

def run_signal_engine(indicator_output:Path,certificate_path:Path,c:SignalConfig,out:Path):
    cert=validate_indicator_certificate(certificate_path); src=locate_indicator_data(indicator_output,cert)
    reg=build_signal_registry(c); rows=build_signals(load_indicator_rows(src),c); stats=validate_signal_rows(rows)
    store=store_signals(out,src,reg,rows,stats); verify_signal_manifest(out,store["manifest"])
    return {"stage":"V79.74","status":"PASS","registry":reg,"stats":stats,**store,
            "source_preserved":src.is_file(),"network_requests_executed":0,"credentials_used":0,
            "trading_client_created":False,"actual_orders_submitted":0}

def build_signal_certificate(root:Path,out:Path,c:SignalConfig,result):
    checks={"v79_70_certificate_present":(root/"release/v79_70/output/historical_indicator_library_certificate_v79_70.json").is_file(),
            "pipeline_status_pass":result["status"]=="PASS","signal_rows_positive":result["stats"]["signal_row_count"]>0,
            "distribution_complete":sum(result["stats"][x] for x in ("buy_count","sell_count","hold_count"))==result["stats"]["signal_row_count"],
            "source_preserved":result["source_preserved"] is True,"manifest_hash_present":len(result["manifest"].get("manifest_sha256",""))==64,
            "network_requests_zero":result["network_requests_executed"]==0,"credentials_unused":result["credentials_used"]==0,
            "trading_client_not_created":result["trading_client_created"] is False,"actual_orders_zero":result["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]; status="PASS" if not failed else "FAIL"
    cert={"stage":"V79.75","status":status,"scope":"OFFLINE_HISTORICAL_SIGNAL_ENGINE",
          "stages_completed":["V79.71","V79.72","V79.73","V79.74","V79.75"],
          "passed_stage_count":5 if status=="PASS" else max(0,5-len(failed)),"failed_stage_count":0 if status=="PASS" else len(failed),
          "config":asdict(c),"signal_summary":{"cache_id":result["cache_id"],"rule_count":result["registry"]["rule_count"],**result["stats"],
          "cache_created":result["created"],"cache_reused":result["reused_existing_cache"],"source_preserved":result["source_preserved"]},
          "signal_manifest":result["manifest"],"checks":checks,"failed_checks":failed,
          "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
          "actual_orders_submitted":0,"live_trading_authorized":False,"next_phase":"V79_76_HISTORICAL_PORTFOLIO_SIMULATION"}
    cert["certificate_sha256"]=hj(cert); cp=out/"historical_signal_engine_certificate_v79_75.json"; wj(cp,cert)
    wj(out/"historical_signal_engine_verify_v79_75.json",{"stage":"V79.75","status":status,"verified":not failed,
       "certificate_sha256":cert["certificate_sha256"],"certificate_path":str(cp.relative_to(root)).replace("\\","/"),"failed_checks":failed})
    return cert

sha256_signal_json=hj
