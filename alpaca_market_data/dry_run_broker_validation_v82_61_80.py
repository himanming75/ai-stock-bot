from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

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
class DryRunBrokerConfig:
    mode:str="DRY_RUN_ONLY"
    max_order_notional:float=1000.0
    max_position_notional:float=5000.0
    buying_power:float=10000.0
    market_open:bool=True
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="DRY_RUN_ONLY": raise ValueError("safe mode")
        if min(self.max_order_notional,self.max_position_notional,self.buying_power)<=0: raise ValueError("limits")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline dry run only")

def validate_connection_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V82.60" or c.get("status")!="PASS": raise ValueError("bad V82.60 certificate")
    if c.get("broker_connection_validation_complete") is not True or c.get("actual_orders_submitted")!=0: raise ValueError("prerequisite")
    return c

def make_intent(symbol,side,quantity,price,order_type="MARKET"):
    side=side.upper();order_type=order_type.upper();symbol=symbol.upper()
    if side not in {"BUY","SELL"} or order_type not in {"MARKET","LIMIT"} or quantity<1 or price<=0: raise ValueError("intent")
    d={"stage":"V82.61","intent_id":"intent-"+hj([symbol,side,quantity,price,order_type])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"reference_price":float(price),"order_type":order_type,
       "submission_authorized":False}
    d["intent_sha256"]=hj(d);return d

def idempotency_key(intent):
    d={"stage":"V82.62","intent_id":intent["intent_id"],
       "idempotency_key":"idem-"+hj(intent)[:24]}
    d["idempotency_sha256"]=hj(d);return d

def duplicate_guard(keys):
    duplicate=len(keys)!=len(set(keys))
    d={"stage":"V82.63","key_count":len(keys),"duplicate_detected":duplicate,
       "accepted":not duplicate}
    d["duplicate_sha256"]=hj(d);return d

def serialize_order(intent):
    d={"stage":"V82.64","payload":{"symbol":intent["symbol"],"side":intent["side"],
       "qty":intent["quantity"],"type":intent["order_type"],"time_in_force":"day"},
       "preview_only":True}
    d["payload_sha256"]=hj(d);return d

def signing_simulation(payload):
    d={"stage":"V82.65","signature":"sim-signature-"+hj(payload)[:32],
       "secret_loaded":False,"valid_for_network":False}
    d["signing_sha256"]=hj(d);return d

def risk_guard(intent,c):
    notional=intent["quantity"]*intent["reference_price"]
    allowed=notional<=c.max_order_notional
    d={"stage":"V82.66","notional":round(notional,8),"limit":c.max_order_notional,
       "allowed":allowed}
    d["risk_sha256"]=hj(d);return d

def buying_power_guard(intent,c):
    required=intent["quantity"]*intent["reference_price"] if intent["side"]=="BUY" else 0.0
    allowed=required<=c.buying_power
    d={"stage":"V82.67","required_buying_power":round(required,8),
       "available_buying_power":c.buying_power,"allowed":allowed}
    d["buying_power_sha256"]=hj(d);return d

def position_guard(intent,current_qty,c):
    projected=current_qty+intent["quantity"] if intent["side"]=="BUY" else current_qty-intent["quantity"]
    allowed=projected>=0 and projected*intent["reference_price"]<=c.max_position_notional
    d={"stage":"V82.68","current_quantity":current_qty,"projected_quantity":projected,
       "projected_notional":round(projected*intent["reference_price"],8),"allowed":allowed}
    d["position_sha256"]=hj(d);return d

def market_session_guard(c):
    d={"stage":"V82.69","market_open":c.market_open,"allowed":c.market_open,
       "network_clock_checked":False}
    d["session_sha256"]=hj(d);return d

def preflight(intent,c,current_qty=0):
    checks={
      "risk":risk_guard(intent,c),
      "buying_power":buying_power_guard(intent,c),
      "position":position_guard(intent,current_qty,c),
      "market_session":market_session_guard(c),
    }
    failed=[k for k,v in checks.items() if not v["allowed"]]
    d={"stage":"V82.70","status":"PASS" if not failed else "REJECTED",
       "checks":checks,"failed_checks":failed,"submission_authorized":False}
    d["preflight_sha256"]=hj(d);return d

REJECTION_MAP={
 "risk":"ORDER_NOTIONAL_LIMIT","buying_power":"INSUFFICIENT_BUYING_POWER",
 "position":"POSITION_LIMIT","market_session":"MARKET_CLOSED","duplicate":"DUPLICATE_ORDER"
}

def rejection_mapping(failed_checks):
    codes=[REJECTION_MAP[x] for x in failed_checks]
    d={"stage":"V82.71","rejection_codes":codes,"rejection_count":len(codes)}
    d["rejection_sha256"]=hj(d);return d

def build_receipt(intent,idem,payload,signing,preflight):
    status="DRY_RUN_ACCEPTED" if preflight["status"]=="PASS" else "DRY_RUN_REJECTED"
    d={"stage":"V82.72","receipt_id":"dryrun-"+hj([intent,idem,preflight])[:24],
       "status":status,"intent_id":intent["intent_id"],"idempotency_key":idem["idempotency_key"],
       "payload_sha256":payload["payload_sha256"],"signature":signing["signature"],
       "failed_checks":preflight["failed_checks"],"actual_order_submitted":False}
    d["receipt_sha256"]=hj(d);return d

def replay_receipt(intent,c,current_qty=0):
    idem=idempotency_key(intent);payload=serialize_order(intent);signing=signing_simulation(payload)
    p1=preflight(intent,c,current_qty);r1=build_receipt(intent,idem,payload,signing,p1)
    p2=preflight(intent,c,current_qty);r2=build_receipt(intent,idem,payload,signing,p2)
    d={"stage":"V82.73","deterministic":r1==r2,"receipt_sha256":r1["receipt_sha256"]}
    d["replay_sha256"]=hj(d);return d

def build_scenarios(c):
    accepted=make_intent("AAPL","BUY",5,100)
    risk_reject=make_intent("MSFT","BUY",20,100)
    bp_reject=make_intent("SPY","BUY",15,800)
    position_reject=make_intent("AAPL","SELL",10,100)
    intents=[accepted,risk_reject,bp_reject,position_reject]
    current=[0,0,0,5]
    rows=[]
    for i,(intent,qty) in enumerate(zip(intents,current),1):
        idem=idempotency_key(intent);payload=serialize_order(intent);signing=signing_simulation(payload)
        pf=preflight(intent,c,qty);receipt=build_receipt(intent,idem,payload,signing,pf)
        rows.append({"scenario":i,"intent":intent,"idempotency":idem,"payload":payload,
                     "signing":signing,"preflight":pf,"receipt":receipt})
    duplicate=duplicate_guard([rows[0]["idempotency"]["idempotency_key"]]*2)
    d={"stage":"V82.74","status":"PASS","scenario_count":len(rows),
       "accepted_count":sum(x["receipt"]["status"]=="DRY_RUN_ACCEPTED" for x in rows),
       "rejected_count":sum(x["receipt"]["status"]=="DRY_RUN_REJECTED" for x in rows),
       "duplicate_detected":duplicate["duplicate_detected"],"rows":rows}
    d["scenario_sha256"]=hj(d);return d

def build_audit(c,scenarios,replay):
    checks={"scenario_count_four":scenarios["scenario_count"]==4,
      "accepted_positive":scenarios["accepted_count"]>0,
      "rejected_positive":scenarios["rejected_count"]>0,
      "duplicate_detected":scenarios["duplicate_detected"],
      "replay_deterministic":replay["deterministic"],
      "network_zero":not c.allow_network,"credentials_zero":not c.allow_credentials,
      "client_false":not c.allow_trading_client,"actual_orders_zero":c.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V82.75","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="dry-run-broker-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V82.76","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"dry_run_broker_master_ledger_v82_76.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"dry_run_broker_master_ledger_v82_76.json";b=lp.read_bytes()
    d={"stage":"V82.77","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"dry_run_broker_manifest_v82_77.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"dry_run_broker_master_ledger_v82_76.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_connection_certificate(root/"release/v82_60/output/broker_connection_validation_certificate_v82_60.json")
    scenarios=build_scenarios(c);replay=replay_receipt(make_intent("AAPL","BUY",5,100),c,0)
    audit=build_audit(c,scenarios,replay)
    docs={"scenarios":scenarios,"replay":replay,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"scenario_count":scenarios["scenario_count"],"accepted_count":scenarios["accepted_count"],
      "rejected_count":scenarios["rejected_count"],"duplicate_detected":scenarios["duplicate_detected"],
      "replay_deterministic":replay["deterministic"],"audit_status":audit["status"],
      "source_connection_validation_complete":source["broker_connection_validation_complete"]}
    return {"stage":"V82.78","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v82_60_certificate_present":(root/"release/v82_60/output/broker_connection_validation_certificate_v82_60.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","scenario_count_four":s["scenario_count"]==4,
      "accepted_positive":s["accepted_count"]>0,"rejected_positive":s["rejected_count"]>0,
      "duplicate_detected":s["duplicate_detected"],"replay_deterministic":s["replay_deterministic"],
      "audit_pass":s["audit_status"]=="PASS","manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V82.80","status":status,"scope":"OFFLINE_DRY_RUN_BROKER_VALIDATION",
      "stages_completed":[f"V82.{i:02d}" for i in range(61,81)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"dry_run_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "dry_run_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_trading_authorized":False,"live_trading_authorized":False,
      "dry_run_broker_validation_complete":status=="PASS",
      "next_phase":"V82_81_PAPER_BROKER_ENABLEMENT_FOUNDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"dry_run_broker_validation_certificate_v82_80.json",cert)
    wj(out/"dry_run_broker_validation_verify_v82_80.json",{"stage":"V82.80","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
