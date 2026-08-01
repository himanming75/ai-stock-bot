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
class PaperBrokerOrderGateConfig:
    mode:str="PAPER_CONNECTION_GATE_OFFLINE"
    environment:str="PAPER"
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
        if self.mode!="PAPER_CONNECTION_GATE_OFFLINE": raise ValueError("safe mode")
        if self.environment!="PAPER": raise ValueError("paper environment")
        if min(self.max_order_notional,self.max_position_notional,self.buying_power)<=0: raise ValueError("limits")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline gate only")

def validate_enablement_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text())
    u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V83.00" or c.get("status")!="PASS": raise ValueError("bad V83.00 certificate")
    if c.get("paper_broker_enablement_complete") is not True or c.get("paper_session_authorized") is not True:
        raise ValueError("enablement prerequisite")
    if c.get("paper_trading_authorized") is not False or c.get("actual_orders_submitted")!=0:
        raise ValueError("unsafe prerequisite")
    return c

def connection_profile():
    d={"stage":"V83.01","provider":"ALPACA_COMPATIBLE","environment":"PAPER",
       "base_url":"https://paper-api.alpaca.markets","network_enabled":False,
       "credentials_loaded":False,"trading_client_created":False}
    d["profile_sha256"]=hj(d);return d

def session_binding(source_cert):
    d={"stage":"V83.02","session_id":"paper-gate-"+hj(source_cert["certificate_sha256"])[:20],
       "source_permission_scope":source_cert["paper_broker_summary"]["permission_scope"],
       "paper_session_authorized":source_cert["paper_session_authorized"],
       "paper_order_submission_authorized":False,"live_trading_authorized":False}
    d["session_sha256"]=hj(d);return d

def order_gate_policy():
    rules={
      "paper_environment_required":True,
      "session_authorization_required":True,
      "risk_check_required":True,
      "buying_power_check_required":True,
      "position_check_required":True,
      "market_session_check_required":True,
      "duplicate_check_required":True,
      "paper_order_submit_enabled":False,
      "live_order_submit_enabled":False,
    }
    d={"stage":"V83.03","status":"PASS","rules":rules}
    d["policy_sha256"]=hj(d);return d

def make_order_intent(symbol,side,quantity,price):
    side=side.upper();symbol=symbol.upper()
    if side not in {"BUY","SELL"} or quantity<1 or price<=0: raise ValueError("intent")
    d={"stage":"V83.04","intent_id":"paper-intent-"+hj([symbol,side,quantity,price])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"reference_price":float(price),
       "environment":"PAPER","submission_authorized":False}
    d["intent_sha256"]=hj(d);return d

def idempotency_key(intent):
    d={"stage":"V83.05","intent_id":intent["intent_id"],"key":"paper-idem-"+hj(intent)[:24]}
    d["idempotency_sha256"]=hj(d);return d

def duplicate_guard(keys):
    duplicate=len(keys)!=len(set(keys))
    d={"stage":"V83.06","key_count":len(keys),"duplicate_detected":duplicate,
       "accepted":not duplicate}
    d["duplicate_sha256"]=hj(d);return d

def environment_guard(intent,config):
    allowed=intent["environment"]=="PAPER" and config.environment=="PAPER"
    d={"stage":"V83.07","intent_environment":intent["environment"],"configured_environment":config.environment,
       "allowed":allowed,"live_environment_allowed":False}
    d["environment_sha256"]=hj(d);return d

def session_guard(session):
    allowed=session["paper_session_authorized"] is True
    d={"stage":"V83.08","session_id":session["session_id"],"allowed":allowed,
       "paper_order_submission_authorized":False}
    d["session_guard_sha256"]=hj(d);return d

def risk_guard(intent,config):
    notional=intent["quantity"]*intent["reference_price"]
    allowed=notional<=config.max_order_notional
    d={"stage":"V83.09","notional":round(notional,8),"limit":config.max_order_notional,"allowed":allowed}
    d["risk_sha256"]=hj(d);return d

def buying_power_guard(intent,config):
    required=intent["quantity"]*intent["reference_price"] if intent["side"]=="BUY" else 0.0
    allowed=required<=config.buying_power
    d={"stage":"V83.10","required":round(required,8),"available":config.buying_power,"allowed":allowed}
    d["buying_power_sha256"]=hj(d);return d

def position_guard(intent,current_qty,config):
    projected=current_qty+intent["quantity"] if intent["side"]=="BUY" else current_qty-intent["quantity"]
    allowed=projected>=0 and projected*intent["reference_price"]<=config.max_position_notional
    d={"stage":"V83.11","current_quantity":current_qty,"projected_quantity":projected,
       "projected_notional":round(projected*intent["reference_price"],8),"allowed":allowed}
    d["position_sha256"]=hj(d);return d

def market_session_guard(config):
    d={"stage":"V83.12","market_open":config.market_open,"allowed":config.market_open,
       "network_clock_checked":False}
    d["market_sha256"]=hj(d);return d

def preflight(intent,session,config,current_qty=0):
    checks={
      "environment":environment_guard(intent,config),
      "session":session_guard(session),
      "risk":risk_guard(intent,config),
      "buying_power":buying_power_guard(intent,config),
      "position":position_guard(intent,current_qty,config),
      "market_session":market_session_guard(config),
    }
    failed=[k for k,v in checks.items() if not v["allowed"]]
    d={"stage":"V83.13","status":"PASS" if not failed else "REJECTED",
       "checks":checks,"failed_checks":failed,
       "paper_order_submission_authorized":False}
    d["preflight_sha256"]=hj(d);return d

def queue_preview(intent,idem,preflight_doc):
    accepted=preflight_doc["status"]=="PASS"
    d={"stage":"V83.14","queue_id":"paper-queue-"+hj([intent,idem])[:20],
       "intent_id":intent["intent_id"],"idempotency_key":idem["key"],
       "queue_status":"PREVIEW_ACCEPTED" if accepted else "PREVIEW_REJECTED",
       "paper_order_submission_authorized":False}
    d["queue_sha256"]=hj(d);return d

def gate_receipt(intent,queue,preflight_doc):
    d={"stage":"V83.15","receipt_id":"paper-gate-receipt-"+hj([intent,queue,preflight_doc])[:24],
       "status":"GATE_PASS" if preflight_doc["status"]=="PASS" else "GATE_REJECTED",
       "failed_checks":preflight_doc["failed_checks"],"queue_status":queue["queue_status"],
       "paper_order_submission_authorized":False,"actual_order_submitted":False}
    d["receipt_sha256"]=hj(d);return d

def build_scenarios(session,config):
    cases=[
      (make_order_intent("AAPL","BUY",5,100),0),
      (make_order_intent("MSFT","BUY",20,100),0),
      (make_order_intent("SPY","SELL",10,100),5),
      (make_order_intent("QQQ","BUY",2,400),0),
    ]
    rows=[]
    for i,(intent,qty) in enumerate(cases,1):
        idem=idempotency_key(intent)
        pf=preflight(intent,session,config,qty)
        queue=queue_preview(intent,idem,pf)
        receipt=gate_receipt(intent,queue,pf)
        rows.append({"scenario":i,"intent":intent,"idempotency":idem,"preflight":pf,"queue":queue,"receipt":receipt})
    dup=duplicate_guard([rows[0]["idempotency"]["key"],rows[0]["idempotency"]["key"]])
    d={"stage":"V83.16","status":"PASS","scenario_count":len(rows),
       "gate_pass_count":sum(x["receipt"]["status"]=="GATE_PASS" for x in rows),
       "gate_reject_count":sum(x["receipt"]["status"]=="GATE_REJECTED" for x in rows),
       "duplicate_detected":dup["duplicate_detected"],"rows":rows}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,profile,session,policy,scenarios):
    checks={"profile_network_disabled":profile["network_enabled"] is False,
      "profile_credentials_unloaded":profile["credentials_loaded"] is False,
      "client_not_created":profile["trading_client_created"] is False,
      "paper_session_authorized":session["paper_session_authorized"] is True,
      "paper_submit_false":session["paper_order_submission_authorized"] is False,
      "live_false":session["live_trading_authorized"] is False,
      "policy_pass":policy["status"]=="PASS",
      "scenario_count_four":scenarios["scenario_count"]==4,
      "gate_pass_positive":scenarios["gate_pass_count"]>0,
      "gate_reject_positive":scenarios["gate_reject_count"]>0,
      "duplicate_detected":scenarios["duplicate_detected"],
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V83.17","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="paper-order-gate-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V83.18","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_order_gate_master_ledger_v83_18.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"paper_order_gate_master_ledger_v83_18.json";b=lp.read_bytes()
    d={"stage":"V83.19","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_order_gate_manifest_v83_19.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"paper_order_gate_master_ledger_v83_18.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_enablement_certificate(root/"release/v83_00/output/paper_broker_enablement_certificate_v83_00.json")
    profile=connection_profile();session=session_binding(source);policy=order_gate_policy()
    scenarios=build_scenarios(session,c);audit=build_audit(c,profile,session,policy,scenarios)
    docs={"connection_profile":profile,"session_binding":session,"order_gate_policy":policy,
          "scenarios":scenarios,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"provider":profile["provider"],"paper_session_authorized":session["paper_session_authorized"],
      "paper_order_submission_authorized":session["paper_order_submission_authorized"],
      "live_trading_authorized":session["live_trading_authorized"],
      "scenario_count":scenarios["scenario_count"],"gate_pass_count":scenarios["gate_pass_count"],
      "gate_reject_count":scenarios["gate_reject_count"],"duplicate_detected":scenarios["duplicate_detected"],
      "audit_status":audit["status"],"source_paper_enablement_complete":source["paper_broker_enablement_complete"]}
    return {"stage":"V83.20","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v83_00_certificate_present":(root/"release/v83_00/output/paper_broker_enablement_certificate_v83_00.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","paper_session_authorized":s["paper_session_authorized"] is True,
      "paper_submit_false":s["paper_order_submission_authorized"] is False,
      "live_not_authorized":s["live_trading_authorized"] is False,
      "scenario_count_four":s["scenario_count"]==4,
      "gate_pass_positive":s["gate_pass_count"]>0,"gate_reject_positive":s["gate_reject_count"]>0,
      "duplicate_detected":s["duplicate_detected"],"audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V83.20","status":status,"scope":"OFFLINE_PAPER_BROKER_CONNECTION_AND_ORDER_GATE",
      "stages_completed":[f"V83.{i:02d}" for i in range(1,21)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"paper_order_gate_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "paper_order_gate_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_session_authorized":s["paper_session_authorized"],
      "paper_order_submission_authorized":False,"paper_trading_authorized":False,
      "live_trading_authorized":False,"paper_order_gate_complete":status=="PASS",
      "next_phase":"V83_21_PAPER_ORDER_AUTHORIZATION_FOUNDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"paper_order_gate_certificate_v83_20.json",cert)
    wj(out/"paper_order_gate_verify_v83_20.json",{"stage":"V83.20","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
