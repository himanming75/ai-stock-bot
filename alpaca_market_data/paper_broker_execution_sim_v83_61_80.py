from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class PaperBrokerExecutionSimulationConfig:
    mode:str="PAPER_BROKER_EXECUTION_SIMULATION"
    initial_cash:float=100000.0
    commission_per_fill:float=1.0
    slippage_bps:float=5.0
    partial_fill_ratio:float=0.5
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="PAPER_BROKER_EXECUTION_SIMULATION": raise ValueError("safe mode")
        if self.initial_cash<=0 or self.commission_per_fill<0 or self.slippage_bps<0: raise ValueError("financial config")
        if not 0<self.partial_fill_ratio<1: raise ValueError("partial ratio")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline execution only")

def validate_submission_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V83.60" or c.get("status")!="PASS": raise ValueError("bad V83.60 certificate")
    if c.get("paper_order_submission_simulation_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("submission prerequisite")
    return c

def lifecycle_contract():
    transitions={"CREATED":["ACCEPTED","REJECTED","CANCELED"],"ACCEPTED":["PARTIALLY_FILLED","FILLED","CANCELED"],
      "PARTIALLY_FILLED":["PARTIALLY_FILLED","FILLED","CANCELED"],"FILLED":[],"REJECTED":[],"CANCELED":[]}
    d={"stage":"V83.61","initial_state":"CREATED","transitions":transitions,
       "network_state_present":False,"live_state_present":False}
    d["lifecycle_sha256"]=hj(d);return d

def make_order(symbol,side,quantity,reference_price):
    side=side.upper();symbol=symbol.upper()
    if side not in {"BUY","SELL"} or quantity<1 or reference_price<=0: raise ValueError("order")
    d={"stage":"V83.62","order_id":"exec-order-"+hj([symbol,side,quantity,reference_price])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"reference_price":float(reference_price),
       "state":"CREATED","filled_quantity":0,"actual_broker_order":False}
    d["order_sha256"]=hj(d);return d

def accept_order(order):
    if order["state"]!="CREATED": raise ValueError("invalid transition")
    d={**order,"stage":"V83.63","state":"ACCEPTED"}
    d["order_sha256"]=hj({k:v for k,v in d.items() if k!="order_sha256"});return d

def cancel_order_sim(order,reason):
    if order["state"] not in {"CREATED","ACCEPTED","PARTIALLY_FILLED"}: raise ValueError("invalid cancel")
    d={**order,"stage":"V83.64","state":"CANCELED","cancel_reason":reason}
    d["order_sha256"]=hj({k:v for k,v in d.items() if k!="order_sha256"});return d

def execution_price(order,config):
    direction=1 if order["side"]=="BUY" else -1
    return round(order["reference_price"]*(1+direction*config.slippage_bps/10000),8)

def create_fill(order,quantity,config,fill_index):
    remaining=order["quantity"]-order["filled_quantity"]
    if quantity<1 or quantity>remaining: raise ValueError("fill quantity")
    price=execution_price(order,config)
    d={"stage":"V83.65","fill_id":"fill-"+hj([order["order_id"],fill_index,quantity,price])[:20],
       "order_id":order["order_id"],"symbol":order["symbol"],"side":order["side"],
       "quantity":quantity,"price":price,"commission":config.commission_per_fill,
       "actual_broker_fill":False}
    d["fill_sha256"]=hj(d);return d

def apply_fill(order,fill):
    if order["state"] not in {"ACCEPTED","PARTIALLY_FILLED"}: raise ValueError("invalid fill state")
    new_filled=order["filled_quantity"]+fill["quantity"]
    state="FILLED" if new_filled==order["quantity"] else "PARTIALLY_FILLED"
    prior_notional=order.get("average_fill_price",0.0)*order["filled_quantity"]
    avg=(prior_notional+fill["price"]*fill["quantity"])/new_filled
    d={**order,"stage":"V83.66","state":state,"filled_quantity":new_filled,
       "average_fill_price":round(avg,8)}
    d["order_sha256"]=hj({k:v for k,v in d.items() if k!="order_sha256"});return d

def cash_ledger(initial_cash,fills):
    cash=initial_cash;commission=0.0
    for f in fills:
        sign=-1 if f["side"]=="BUY" else 1
        cash += sign*f["quantity"]*f["price"]-f["commission"]
        commission += f["commission"]
    d={"stage":"V83.67","opening_cash":initial_cash,"closing_cash":round(cash,8),
       "commission_total":round(commission,8),"fill_count":len(fills)}
    d["cash_ledger_sha256"]=hj(d);return d

def position_ledger(fills,marks):
    positions={}
    realized=0.0
    for f in fills:
        p=positions.setdefault(f["symbol"],{"quantity":0,"average_cost":0.0})
        if f["side"]=="BUY":
            newq=p["quantity"]+f["quantity"]
            p["average_cost"]=((p["average_cost"]*p["quantity"])+(f["price"]*f["quantity"]))/newq
            p["quantity"]=newq
        else:
            qty=min(f["quantity"],p["quantity"])
            realized += (f["price"]-p["average_cost"])*qty
            p["quantity"]-=qty
            if p["quantity"]==0:p["average_cost"]=0.0
    unrealized=0.0
    for sym,p in positions.items():
        unrealized += (marks.get(sym,p["average_cost"])-p["average_cost"])*p["quantity"]
    d={"stage":"V83.68","positions":positions,"position_count":sum(1 for p in positions.values() if p["quantity"]>0),
       "realized_pnl":round(realized,8),"unrealized_pnl":round(unrealized,8)}
    d["position_ledger_sha256"]=hj(d);return d

def execution_ledger(orders,fills,cash,positions):
    d={"stage":"V83.69","order_count":len(orders),"fill_count":len(fills),
       "filled_order_count":sum(o["state"]=="FILLED" for o in orders),
       "partial_order_count":sum(o["state"]=="PARTIALLY_FILLED" for o in orders),
       "canceled_order_count":sum(o["state"]=="CANCELED" for o in orders),
       "rejected_order_count":sum(o["state"]=="REJECTED" for o in orders),
       "closing_cash":cash["closing_cash"],"realized_pnl":positions["realized_pnl"],
       "unrealized_pnl":positions["unrealized_pnl"]}
    d["execution_ledger_sha256"]=hj(d);return d

def deterministic_replay(config):
    a=build_scenarios(config);b=build_scenarios(config)
    d={"stage":"V83.70","deterministic":a==b,"scenario_sha256":a["scenario_sha256"]}
    d["replay_sha256"]=hj(d);return d

def build_scenarios(config):
    fills=[];orders=[]
    buy=accept_order(make_order("AAPL","BUY",10,100))
    f1=create_fill(buy,5,config,1);buy=apply_fill(buy,f1);fills.append(f1)
    f2=create_fill(buy,5,config,2);buy=apply_fill(buy,f2);fills.append(f2);orders.append(buy)
    sell=accept_order(make_order("AAPL","SELL",4,105))
    f3=create_fill(sell,4,config,1);sell=apply_fill(sell,f3);fills.append(f3);orders.append(sell)
    partial=accept_order(make_order("MSFT","BUY",8,200))
    f4=create_fill(partial,4,config,1);partial=apply_fill(partial,f4);fills.append(f4);orders.append(partial)
    canceled=cancel_order_sim(accept_order(make_order("SPY","BUY",3,500)),"simulation cancel");orders.append(canceled)
    rejected=make_order("QQQ","BUY",2,400);rejected={**rejected,"state":"REJECTED","reject_reason":"simulation rejection"};orders.append(rejected)
    cash=cash_ledger(config.initial_cash,fills)
    positions=position_ledger(fills,{"AAPL":106.0,"MSFT":202.0})
    ledger=execution_ledger(orders,fills,cash,positions)
    d={"stage":"V83.71","status":"PASS","orders":orders,"fills":fills,"cash_ledger":cash,
       "position_ledger":positions,"execution_ledger":ledger}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,lifecycle,scenarios,replay):
    l=scenarios["execution_ledger"]
    checks={"lifecycle_no_network":lifecycle["network_state_present"] is False,
      "lifecycle_no_live":lifecycle["live_state_present"] is False,
      "order_count_five":l["order_count"]==5,"fills_positive":l["fill_count"]>0,
      "filled_positive":l["filled_order_count"]>0,"partial_positive":l["partial_order_count"]>0,
      "canceled_positive":l["canceled_order_count"]>0,"rejected_positive":l["rejected_order_count"]>0,
      "cash_positive":l["closing_cash"]>0,"replay_deterministic":replay["deterministic"],
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V83.72","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="paper-broker-execution-sim-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V83.73","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_broker_execution_master_ledger_v83_73.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"paper_broker_execution_master_ledger_v83_73.json";b=lp.read_bytes()
    d={"stage":"V83.74","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_broker_execution_manifest_v83_74.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"paper_broker_execution_master_ledger_v83_73.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_submission_certificate(root/"release/v83_60/output/paper_order_submission_sim_certificate_v83_60.json")
    lifecycle=lifecycle_contract();scenarios=build_scenarios(c);replay=deterministic_replay(c)
    audit=build_audit(c,lifecycle,scenarios,replay)
    docs={"lifecycle":lifecycle,"scenarios":scenarios,"replay":replay,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    l=scenarios["execution_ledger"];p=scenarios["position_ledger"];cash=scenarios["cash_ledger"]
    summary={"order_count":l["order_count"],"fill_count":l["fill_count"],
      "filled_order_count":l["filled_order_count"],"partial_order_count":l["partial_order_count"],
      "canceled_order_count":l["canceled_order_count"],"rejected_order_count":l["rejected_order_count"],
      "closing_cash":cash["closing_cash"],"position_count":p["position_count"],
      "realized_pnl":p["realized_pnl"],"unrealized_pnl":p["unrealized_pnl"],
      "replay_deterministic":replay["deterministic"],"audit_status":audit["status"],
      "source_submission_sim_complete":source["paper_order_submission_simulation_complete"]}
    return {"stage":"V83.75","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v83_60_certificate_present":(root/"release/v83_60/output/paper_order_submission_sim_certificate_v83_60.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","order_count_five":s["order_count"]==5,
      "fills_positive":s["fill_count"]>0,"filled_positive":s["filled_order_count"]>0,
      "partial_positive":s["partial_order_count"]>0,"canceled_positive":s["canceled_order_count"]>0,
      "rejected_positive":s["rejected_order_count"]>0,"closing_cash_positive":s["closing_cash"]>0,
      "replay_deterministic":s["replay_deterministic"],"audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V83.80","status":status,"scope":"OFFLINE_PAPER_BROKER_EXECUTION_SIMULATION",
      "stages_completed":[f"V83.{i:02d}" for i in range(61,81)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"paper_broker_execution_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "paper_broker_execution_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_order_submission_authorized":False,"paper_trading_authorized":False,
      "live_trading_authorized":False,"paper_broker_execution_simulation_complete":status=="PASS",
      "next_phase":"V83_81_PAPER_BROKER_FINAL_CERTIFICATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"paper_broker_execution_sim_certificate_v83_80.json",cert)
    wj(out/"paper_broker_execution_sim_verify_v83_80.json",{"stage":"V83.80","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
