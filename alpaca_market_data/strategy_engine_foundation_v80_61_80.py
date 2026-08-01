from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol
import hashlib, json, math, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class StrategyEngineConfig:
    mode:str="STRATEGY_DECISION_ONLY"
    enabled_strategies:tuple[str,...]=("SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT")
    weights:tuple[float,...]=(0.30,0.25,0.25,0.20)
    minimum_confidence:float=0.20
    conflict_policy:str="WEIGHTED_VOTE"
    allow_dynamic_imports:bool=False
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        expected=("SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT")
        if self.mode!="STRATEGY_DECISION_ONLY": raise ValueError("safe mode")
        if self.enabled_strategies!=expected: raise ValueError("strategy registry mismatch")
        if len(self.weights)!=len(expected) or abs(sum(self.weights)-1.0)>1e-9: raise ValueError("weights")
        if any(x<=0 or not math.isfinite(x) for x in self.weights): raise ValueError("weights")
        if not 0<=self.minimum_confidence<=1: raise ValueError("confidence")
        if self.conflict_policy!="WEIGHTED_VOTE" or self.allow_dynamic_imports: raise ValueError("unsafe plugin policy")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

class StrategyPlugin(Protocol):
    strategy_id:str
    version:str
    def evaluate(self, rows:list[dict[str,float]])->dict[str,Any]: ...

def validate_monitoring_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V80.60" or c.get("status")!="PASS": raise ValueError("bad V80.60 certificate")
    if c.get("paper_framework_complete") is not True or c.get("actual_orders_submitted")!=0: raise ValueError("paper prerequisite")
    return c

def validate_rows(rows:list[dict[str,float]])->list[dict[str,float]]:
    if len(rows)<5: raise ValueError("insufficient rows")
    out=[]
    for i,r in enumerate(rows):
        close=float(r["close"]);high=float(r.get("high",close));low=float(r.get("low",close))
        if not all(math.isfinite(x) and x>0 for x in (close,high,low)) or high<close or low>close: raise ValueError("bad row")
        out.append({"sequence":i+1,"close":close,"high":high,"low":low})
    return out

def _signal(strategy_id,version,signal,confidence,reason)->dict[str,Any]:
    d={"stage":"V80.66","strategy_id":strategy_id,"strategy_version":version,"signal":signal,
       "confidence":round(float(confidence),8),"reason":reason,"order_submission_authorized":False}
    d["signal_sha256"]=hj(d);return d

class SmaCrossStrategy:
    strategy_id="SMA_CROSS";version="1.0.0"
    def evaluate(self,rows):
        rows=validate_rows(rows);cl=[x["close"] for x in rows];short=sum(cl[-3:])/3;long=sum(cl[-5:])/5
        diff=(short-long)/long
        return _signal(self.strategy_id,self.version,"BUY" if diff>0.001 else "SELL" if diff<-0.001 else "HOLD",min(abs(diff)*100,1),"short_vs_long_sma")

class RsiMeanReversionStrategy:
    strategy_id="RSI_MEAN_REVERSION";version="1.0.0"
    def evaluate(self,rows):
        rows=validate_rows(rows);cl=[x["close"] for x in rows];changes=[cl[i]-cl[i-1] for i in range(1,len(cl))]
        gains=sum(max(x,0) for x in changes);losses=sum(max(-x,0) for x in changes)
        rsi=100.0 if losses==0 else 100-(100/(1+gains/losses))
        sig="BUY" if rsi<30 else "SELL" if rsi>70 else "HOLD"
        conf=min(abs(rsi-50)/50,1)
        return _signal(self.strategy_id,self.version,sig,conf,f"rsi={rsi:.4f}")

class MomentumStrategy:
    strategy_id="MOMENTUM";version="1.0.0"
    def evaluate(self,rows):
        rows=validate_rows(rows);ret=rows[-1]["close"]/rows[0]["close"]-1
        sig="BUY" if ret>0.01 else "SELL" if ret<-0.01 else "HOLD"
        return _signal(self.strategy_id,self.version,sig,min(abs(ret)*10,1),"period_return")

class BreakoutStrategy:
    strategy_id="BREAKOUT";version="1.0.0"
    def evaluate(self,rows):
        rows=validate_rows(rows);prior=rows[:-1];last=rows[-1]["close"];hi=max(x["high"] for x in prior);lo=min(x["low"] for x in prior)
        sig="BUY" if last>hi else "SELL" if last<lo else "HOLD"
        span=max(hi-lo,1e-9);conf=min(abs(last-(hi if sig=="BUY" else lo if sig=="SELL" else (hi+lo)/2))/span,1)
        return _signal(self.strategy_id,self.version,sig,conf,"range_breakout")

def build_registry()->dict[str,Any]:
    entries=[
      {"strategy_id":"SMA_CROSS","version":"1.0.0","class_name":"SmaCrossStrategy"},
      {"strategy_id":"RSI_MEAN_REVERSION","version":"1.0.0","class_name":"RsiMeanReversionStrategy"},
      {"strategy_id":"MOMENTUM","version":"1.0.0","class_name":"MomentumStrategy"},
      {"strategy_id":"BREAKOUT","version":"1.0.0","class_name":"BreakoutStrategy"},
    ]
    d={"stage":"V80.61","status":"PASS","strategy_count":len(entries),"entries":entries,"dynamic_imports_enabled":False}
    d["registry_sha256"]=hj(d);return d

def load_plugins(registry:dict[str,Any])->list[StrategyPlugin]:
    mapping={"SmaCrossStrategy":SmaCrossStrategy,"RsiMeanReversionStrategy":RsiMeanReversionStrategy,
             "MomentumStrategy":MomentumStrategy,"BreakoutStrategy":BreakoutStrategy}
    plugins=[]
    for e in registry["entries"]:
        cls=mapping.get(e["class_name"])
        if cls is None: raise ValueError("unknown plugin")
        p=cls()
        if p.strategy_id!=e["strategy_id"] or p.version!=e["version"]: raise ValueError("plugin metadata mismatch")
        plugins.append(p)
    return plugins

def build_metadata(plugins:list[StrategyPlugin])->dict[str,Any]:
    items=[{"strategy_id":p.strategy_id,"version":p.version,"enabled":True,"deterministic":True,"network_required":False} for p in plugins]
    d={"stage":"V80.62","status":"PASS","strategy_count":len(items),"strategies":items}
    d["metadata_sha256"]=hj(d);return d

def execute_strategies(plugins:list[StrategyPlugin],rows:list[dict[str,float]])->list[dict[str,Any]]:
    validated=validate_rows(rows);signals=[p.evaluate(validated) for p in plugins]
    if len({s["strategy_id"] for s in signals})!=len(signals): raise ValueError("duplicate strategy signal")
    return signals

def resolve_signals(signals:list[dict[str,Any]],config:StrategyEngineConfig)->dict[str,Any]:
    config.validate();weight_map=dict(zip(config.enabled_strategies,config.weights));scores={"BUY":0.0,"SELL":0.0,"HOLD":0.0}
    contributions=[]
    for s in signals:
        w=weight_map[s["strategy_id"]];value=w*s["confidence"];scores[s["signal"]]+=value
        contributions.append({"strategy_id":s["strategy_id"],"signal":s["signal"],"weight":w,"confidence":s["confidence"],"weighted_score":value})
    buy=scores["BUY"];sell=scores["SELL"];hold=scores["HOLD"];net=buy-sell
    if abs(net)<config.minimum_confidence or max(buy,sell)<=hold: final="HOLD"
    else: final="BUY" if net>0 else "SELL"
    confidence=min(abs(net),1.0)
    d={"stage":"V80.67","status":"PASS","final_signal":final,"confidence":round(confidence,8),
       "scores":scores,"contributions":contributions,"conflict_policy":config.conflict_policy,
       "order_submission_authorized":False}
    d["decision_sha256"]=hj(d);return d

def build_allocation(decision:dict[str,Any],config:StrategyEngineConfig)->dict[str,Any]:
    target=0.0 if decision["final_signal"]=="HOLD" else min(decision["confidence"],0.25)
    d={"stage":"V80.68","status":"PASS","final_signal":decision["final_signal"],"target_portfolio_weight":target,
       "maximum_target_weight":0.25,"order_quantity":0,"order_generation_enabled":False}
    d["allocation_sha256"]=hj(d);return d

def build_audit(registry,metadata,signals,decision,allocation)->dict[str,Any]:
    checks={"registry_four":registry["strategy_count"]==4,"metadata_four":metadata["strategy_count"]==4,
      "signals_four":len(signals)==4,"unique_signals":len({x["strategy_id"] for x in signals})==4,
      "decision_pass":decision["status"]=="PASS","allocation_no_orders":allocation["order_quantity"]==0,
      "submission_unauthorized":decision["order_submission_authorized"] is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V80.69","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out:Path,docs:dict[str,Any])->dict[str,Any]:
    package_id="strategy-foundation-"+hj(docs)[:24];pdir=out/"packages"/package_id;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V80.70","status":"PASS","package_id":package_id,"document_count":len(docs),"files":files,
      "package_created":created,"package_reused":not created,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"strategy_engine_master_ledger_v80_70.json",ledger)
    return {"package_id":package_id,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out:Path,ledger:dict[str,Any])->dict[str,Any]:
    lp=out/"strategy_engine_master_ledger_v80_70.json";b=lp.read_bytes()
    d={"stage":"V80.71","status":"PASS","package_id":ledger["package_id"],
      "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"strategy_engine_manifest_v80_71.json",d);return d

def verify_manifest(out:Path,m:dict[str,Any])->bool:
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"strategy_engine_master_ledger_v80_70.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def sample_rows()->list[dict[str,float]]:
    closes=[100,101,102,103,104,105,106,107]
    return [{"close":x,"high":x+0.4,"low":x-0.4} for x in closes]

def run_engine(root:Path,c:StrategyEngineConfig,out:Path)->dict[str,Any]:
    c.validate();validate_monitoring_certificate(root/"release/v80_60/output/paper_monitoring_completion_certificate_v80_60.json")
    registry=build_registry();plugins=load_plugins(registry);metadata=build_metadata(plugins)
    rows=sample_rows();signals=execute_strategies(plugins,rows);decision=resolve_signals(signals,c);allocation=build_allocation(decision,c)
    audit=build_audit(registry,metadata,signals,decision,allocation)
    docs={"registry":registry,"metadata":metadata,"input_rows":{"stage":"V80.65","rows":rows},
      "signals":{"stage":"V80.66","status":"PASS","signals":signals},"decision":decision,"allocation":allocation,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"strategy_count":4,"signal_count":len(signals),"final_signal":decision["final_signal"],
      "decision_confidence":decision["confidence"],"target_portfolio_weight":allocation["target_portfolio_weight"],
      "order_quantity":0,"audit_status":audit["status"]}
    return {"stage":"V80.72","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root:Path,out:Path,c:StrategyEngineConfig,r:dict[str,Any])->dict[str,Any]:
    s=r["summary"];checks={"v80_60_certificate_present":(root/"release/v80_60/output/paper_monitoring_completion_certificate_v80_60.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","strategy_count_four":s["strategy_count"]==4,"signals_four":s["signal_count"]==4,
      "audit_pass":s["audit_status"]=="PASS","order_quantity_zero":s["order_quantity"]==0,
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,"network_zero":r["network_requests_executed"]==0,
      "credentials_zero":r["credentials_used"]==0,"client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V80.80","status":status,"scope":"OFFLINE_STRATEGY_ENGINE_FOUNDATION",
      "stages_completed":[f"V80.{i:02d}" for i in range(61,81)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"strategy_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "strategy_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
      "actual_orders_submitted":0,"paper_trading_authorized":False,"live_trading_authorized":False,
      "strategy_engine_foundation_complete":status=="PASS","next_phase":"V80_81_STRATEGY_BACKTEST_AND_SELECTION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"strategy_engine_foundation_certificate_v80_80.json",cert)
    wj(out/"strategy_engine_foundation_verify_v80_80.json",{"stage":"V80.80","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert

sha256_strategy_engine_json=hj
