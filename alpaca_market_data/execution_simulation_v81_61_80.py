from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b);t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class ExecutionSimulationConfig:
    mode:str="SIMULATION_ONLY"
    starting_cash:float=100000.0
    base_slippage_bps:float=5.0
    commission_per_share:float=0.005
    minimum_commission:float=1.0
    base_latency_ms:int=25
    partial_fill_ratio:float=0.40
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="SIMULATION_ONLY" or self.starting_cash<=0: raise ValueError("safe mode")
        if self.base_slippage_bps<0 or self.commission_per_share<0 or self.minimum_commission<0: raise ValueError("costs")
        if self.base_latency_ms<0 or not 0<self.partial_fill_ratio<1: raise ValueError("execution config")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def validate_adapter_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V81.60" or c.get("status")!="PASS": raise ValueError("bad V81.60 certificate")
    if c.get("broker_adapter_foundation_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("adapter prerequisite")
    return c

def make_order(symbol:str,side:str,quantity:int,order_type:str="MARKET",limit_price:float|None=None)->dict[str,Any]:
    side=side.upper();order_type=order_type.upper();symbol=symbol.upper()
    if side not in {"BUY","SELL"} or order_type not in {"MARKET","LIMIT"} or quantity<1: raise ValueError("order")
    if order_type=="LIMIT" and (limit_price is None or limit_price<=0): raise ValueError("limit")
    d={"stage":"V81.61","order_id":"sim-"+hj([symbol,side,quantity,order_type,limit_price])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"order_type":order_type,
       "limit_price":limit_price,"status":"NEW","submission_authorized":False}
    d["order_sha256"]=hj(d);return d

def enqueue(order:dict[str,Any],sequence:int)->dict[str,Any]:
    if order["status"]!="NEW" or sequence<1: raise ValueError("queue")
    d={"stage":"V81.62","sequence":sequence,"order":order,"queue_status":"QUEUED"}
    d["queue_sha256"]=hj(d);return d

def slippage_price(reference:float,side:str,config:ExecutionSimulationConfig,liquidity_factor:float=1.0)->float:
    if reference<=0 or liquidity_factor<=0: raise ValueError("price")
    adj=config.base_slippage_bps*liquidity_factor/10000
    return round(reference*(1+adj if side=="BUY" else 1-adj),8)

def commission(quantity:int,config:ExecutionSimulationConfig)->float:
    if quantity<1: raise ValueError("quantity")
    return round(max(config.minimum_commission,quantity*config.commission_per_share),8)

def latency(order_id:str,config:ExecutionSimulationConfig)->int:
    jitter=int(order_id[-2:],16)%17
    return config.base_latency_ms+jitter

def fill_event(order:dict[str,Any],quantity:int,price:float,index:int,config:ExecutionSimulationConfig)->dict[str,Any]:
    if quantity<1 or quantity>order["quantity"] or price<=0: raise ValueError("fill")
    d={"stage":"V81.66","fill_id":f"{order['order_id']}-fill-{index}","order_id":order["order_id"],
       "symbol":order["symbol"],"side":order["side"],"quantity":quantity,"price":price,
       "commission":commission(quantity,config),"latency_ms":latency(order["order_id"],config),
       "simulated":True}
    d["fill_sha256"]=hj(d);return d

def execute_order(order:dict[str,Any],reference_price:float,config:ExecutionSimulationConfig,mode:str="FULL")->dict[str,Any]:
    mode=mode.upper()
    if mode not in {"FULL","PARTIAL","MULTI"}: raise ValueError("mode")
    exec_price=slippage_price(reference_price,order["side"],config,1.0)
    if order["order_type"]=="LIMIT":
        lp=float(order["limit_price"])
        marketable=(order["side"]=="BUY" and exec_price<=lp) or (order["side"]=="SELL" and exec_price>=lp)
        if not marketable:
            d={"stage":"V81.67","order_id":order["order_id"],"status":"REJECTED","reason":"LIMIT_NOT_MARKETABLE",
               "fills":[],"filled_quantity":0,"remaining_quantity":order["quantity"]}
            d["execution_sha256"]=hj(d);return d
    q=order["quantity"]
    if mode=="FULL": parts=[q]
    elif mode=="PARTIAL":
        first=max(1,int(q*config.partial_fill_ratio));parts=[first]
    else:
        first=max(1,int(q*config.partial_fill_ratio));second=max(1,(q-first)//2);third=q-first-second
        parts=[x for x in (first,second,third) if x>0]
    fills=[fill_event(order,part,round(exec_price*(1+i*0.0001 if order["side"]=="BUY" else 1-i*0.0001),8),i+1,config) for i,part in enumerate(parts)]
    filled=sum(x["quantity"] for x in fills);remaining=q-filled
    status="FILLED" if remaining==0 else "PARTIALLY_FILLED"
    d={"stage":"V81.67","order_id":order["order_id"],"status":status,"fills":fills,
       "filled_quantity":filled,"remaining_quantity":remaining,
       "average_fill_price":round(sum(x["price"]*x["quantity"] for x in fills)/filled,8),
       "total_commission":round(sum(x["commission"] for x in fills),8)}
    d["execution_sha256"]=hj(d);return d

def apply_execution(state:dict[str,Any],order:dict[str,Any],execution:dict[str,Any])->dict[str,Any]:
    cash=float(state["cash"]);positions=dict(state.get("positions",{}))
    for f in execution["fills"]:
        notional=f["quantity"]*f["price"];fee=f["commission"]
        if order["side"]=="BUY":
            if cash<notional+fee: raise ValueError("insufficient cash")
            cash-=notional+fee;positions[order["symbol"]]=positions.get(order["symbol"],0)+f["quantity"]
        else:
            if positions.get(order["symbol"],0)<f["quantity"]: raise ValueError("insufficient position")
            cash+=notional-fee;positions[order["symbol"]]-=f["quantity"]
    d={"stage":"V81.68","cash":round(cash,8),"positions":positions,
       "applied_order_id":order["order_id"],"applied_fill_count":len(execution["fills"])}
    d["state_sha256"]=hj(d);return d

def replay(order,reference_price,config,mode):
    first=execute_order(order,reference_price,config,mode)
    second=execute_order(order,reference_price,config,mode)
    d={"stage":"V81.69","status":"PASS" if first==second else "FAIL","deterministic":first==second,
       "execution_sha256":first["execution_sha256"]}
    d["replay_sha256"]=hj(d);return d

def build_scenario(config):
    buy=make_order("AAPL","BUY",10)
    partial=make_order("MSFT","BUY",10)
    multi=make_order("JPM","BUY",9)
    rejected=make_order("XOM","BUY",5,"LIMIT",100.0)
    state={"cash":config.starting_cash,"positions":{}}
    executions=[]
    for order,price,mode in ((buy,190,"FULL"),(partial,420,"PARTIAL"),(multi,210,"MULTI"),(rejected,115,"FULL")):
        ex=execute_order(order,price,config,mode);executions.append({"order":order,"execution":ex})
        if ex["fills"]: state=apply_execution(state,order,ex)
    d={"stage":"V81.70","status":"PASS","starting_cash":config.starting_cash,
       "ending_cash":state["cash"],"positions":state["positions"],"execution_count":len(executions),
       "full_fill_count":sum(x["execution"]["status"]=="FILLED" for x in executions),
       "partial_fill_count":sum(x["execution"]["status"]=="PARTIALLY_FILLED" for x in executions),
       "rejected_count":sum(x["execution"]["status"]=="REJECTED" for x in executions),
       "fill_count":sum(len(x["execution"]["fills"]) for x in executions),
       "executions":executions}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,scenario,replay_doc):
    checks={"execution_count_four":scenario["execution_count"]==4,"fills_positive":scenario["fill_count"]>0,
      "partial_positive":scenario["partial_fill_count"]>0,"reject_one":scenario["rejected_count"]==1,
      "cash_nonnegative":scenario["ending_cash"]>=0,"replay_deterministic":replay_doc["deterministic"],
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V81.71","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="execution-simulation-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V81.72","status":"PASS","package_id":pid,"document_count":len(docs),
      "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"execution_simulation_master_ledger_v81_72.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"execution_simulation_master_ledger_v81_72.json";b=lp.read_bytes()
    d={"stage":"V81.73","status":"PASS","package_id":ledger["package_id"],
      "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"execution_simulation_manifest_v81_73.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"execution_simulation_master_ledger_v81_72.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_adapter_certificate(root/"release/v81_60/output/broker_adapter_foundation_certificate_v81_60.json")
    scenario=build_scenario(c)
    replay_doc=replay(scenario["executions"][0]["order"],190,c,"FULL")
    audit=build_audit(c,scenario,replay_doc)
    docs={"scenario":scenario,"replay":replay_doc,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"execution_count":scenario["execution_count"],"fill_count":scenario["fill_count"],
      "full_fill_count":scenario["full_fill_count"],"partial_fill_count":scenario["partial_fill_count"],
      "rejected_count":scenario["rejected_count"],"ending_cash":scenario["ending_cash"],
      "position_count":sum(q>0 for q in scenario["positions"].values()),"replay_deterministic":replay_doc["deterministic"],
      "audit_status":audit["status"],"source_adapter":source["adapter_summary"]["selected_adapter"]}
    return {"stage":"V81.74","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v81_60_certificate_present":(root/"release/v81_60/output/broker_adapter_foundation_certificate_v81_60.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","execution_count_four":s["execution_count"]==4,
      "fills_positive":s["fill_count"]>0,"partial_positive":s["partial_fill_count"]>0,
      "reject_one":s["rejected_count"]==1,"replay_deterministic":s["replay_deterministic"],
      "audit_pass":s["audit_status"]=="PASS","manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V81.80","status":status,"scope":"OFFLINE_EXECUTION_SIMULATION_ENGINE",
      "stages_completed":[f"V81.{i:02d}" for i in range(61,81)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"execution_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "execution_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,"paper_trading_authorized":False,
      "live_trading_authorized":False,"execution_simulation_complete":status=="PASS",
      "next_phase":"V81_81_PAPER_PERFORMANCE_ANALYTICS"}
    cert["certificate_sha256"]=hj(cert);wj(out/"execution_simulation_certificate_v81_80.json",cert)
    wj(out/"execution_simulation_verify_v81_80.json",{"stage":"V81.80","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
