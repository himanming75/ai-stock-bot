from __future__ import annotations
from dataclasses import dataclass, asdict
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
class LiveOrderGateConfig:
    mode:str="LIVE_ORDER_GATE_OFFLINE"
    environment:str="LIVE"
    required_approvals:int=3
    max_order_notional:float=500.0
    max_position_notional:float=2500.0
    max_daily_loss:float=250.0
    max_gross_exposure:float=5000.0
    buying_power:float=10000.0
    kill_switch_armed:bool=True
    emergency_stop_ready:bool=True
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="LIVE_ORDER_GATE_OFFLINE": raise ValueError("safe mode")
        if self.environment!="LIVE": raise ValueError("live environment")
        if self.required_approvals<3: raise ValueError("approval threshold")
        if min(self.max_order_notional,self.max_position_notional,self.max_daily_loss,self.max_gross_exposure,self.buying_power)<=0:
            raise ValueError("risk limits")
        if not self.kill_switch_armed or not self.emergency_stop_ready: raise ValueError("safety state")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline gate only")

def validate_enablement_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V84.20" or c.get("status")!="PASS": raise ValueError("bad V84.20 certificate")
    if c.get("live_enablement_foundation_complete") is not True: raise ValueError("foundation prerequisite")
    if c.get("live_trading_authorized") is not False or c.get("live_order_submission_authorized") is not False:
        raise ValueError("unsafe prerequisite")
    if c.get("actual_orders_submitted")!=0: raise ValueError("unsafe orders")
    return c

def gate_policy():
    rules={"environment_required":True,"approval_required":True,"kill_switch_required":True,
      "emergency_stop_required":True,"account_required":True,"buying_power_required":True,
      "position_limit_required":True,"daily_loss_limit_required":True,"exposure_limit_required":True,
      "duplicate_guard_required":True,"replay_guard_required":True,
      "network_submission_enabled":False,"live_order_submit_enabled":False}
    d={"stage":"V84.21","status":"PASS","rules":rules}
    d["policy_sha256"]=hj(d);return d

def make_live_intent(symbol,side,quantity,reference_price):
    side=side.upper();symbol=symbol.upper()
    if side not in {"BUY","SELL"} or quantity<1 or reference_price<=0: raise ValueError("intent")
    d={"stage":"V84.22","intent_id":"live-intent-"+hj([symbol,side,quantity,reference_price])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"reference_price":float(reference_price),
       "environment":"LIVE","live_order_submission_authorized":False}
    d["intent_sha256"]=hj(d);return d

def idempotency_key(intent):
    d={"stage":"V84.23","intent_id":intent["intent_id"],"key":"live-idem-"+hj(intent)[:24]}
    d["idempotency_sha256"]=hj(d);return d

def duplicate_guard(keys):
    duplicate=len(keys)!=len(set(keys))
    d={"stage":"V84.24","key_count":len(keys),"duplicate_detected":duplicate,"accepted":not duplicate}
    d["duplicate_sha256"]=hj(d);return d

def environment_gate(intent,config):
    allowed=intent["environment"]=="LIVE" and config.environment=="LIVE"
    d={"stage":"V84.25","intent_environment":intent["environment"],"configured_environment":config.environment,
       "allowed":allowed,"environment_switch_allowed":False}
    d["environment_gate_sha256"]=hj(d);return d

def approval_gate(approval_count,config):
    allowed=approval_count>=config.required_approvals
    d={"stage":"V84.26","approval_count":approval_count,"required_approvals":config.required_approvals,
       "allowed":allowed,"live_order_submission_authorized":False}
    d["approval_gate_sha256"]=hj(d);return d

def kill_switch_gate(config):
    allowed=config.kill_switch_armed
    d={"stage":"V84.27","kill_switch_state":"ARMED" if allowed else "DISARMED",
       "allowed":allowed,"blocks_submission":True}
    d["kill_switch_gate_sha256"]=hj(d);return d

def emergency_stop_gate(config):
    allowed=config.emergency_stop_ready
    d={"stage":"V84.28","emergency_stop_state":"READY" if allowed else "NOT_READY",
       "allowed":allowed,"network_halt_supported":False}
    d["emergency_gate_sha256"]=hj(d);return d

def account_gate(account):
    checks={"active":account["status"]=="ACTIVE","equity_positive":account["equity"]>0,
      "buying_power_nonnegative":account["buying_power"]>=0,"trading_blocked":account["trading_blocked"] is True,
      "fixture_source":account["source"]=="OFFLINE_FIXTURE"}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.29","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
       "allowed":not failed}
    d["account_gate_sha256"]=hj(d);return d

def buying_power_gate(intent,config):
    required=intent["quantity"]*intent["reference_price"] if intent["side"]=="BUY" else 0.0
    allowed=required<=config.buying_power
    d={"stage":"V84.30","required":round(required,8),"available":config.buying_power,"allowed":allowed}
    d["buying_power_gate_sha256"]=hj(d);return d

def position_gate(intent,current_qty,config):
    projected=current_qty+intent["quantity"] if intent["side"]=="BUY" else current_qty-intent["quantity"]
    projected_notional=abs(projected*intent["reference_price"])
    allowed=projected>=0 and projected_notional<=config.max_position_notional
    d={"stage":"V84.31","current_quantity":current_qty,"projected_quantity":projected,
       "projected_notional":round(projected_notional,8),"limit":config.max_position_notional,"allowed":allowed}
    d["position_gate_sha256"]=hj(d);return d

def daily_loss_gate(realized_pnl,config):
    loss=max(0.0,-realized_pnl);allowed=loss<=config.max_daily_loss
    d={"stage":"V84.32","realized_pnl":realized_pnl,"daily_loss":loss,
       "loss_limit":config.max_daily_loss,"allowed":allowed,"halt_required":not allowed}
    d["daily_loss_gate_sha256"]=hj(d);return d

def exposure_gate(current_exposure,intent,config):
    delta=intent["quantity"]*intent["reference_price"]
    projected=current_exposure+delta if intent["side"]=="BUY" else max(0.0,current_exposure-delta)
    allowed=projected<=config.max_gross_exposure
    d={"stage":"V84.33","current_exposure":current_exposure,"projected_exposure":round(projected,8),
       "limit":config.max_gross_exposure,"allowed":allowed}
    d["exposure_gate_sha256"]=hj(d);return d

def preflight(intent,approval_count,account,current_qty,realized_pnl,current_exposure,config):
    checks={"environment":environment_gate(intent,config),"approval":approval_gate(approval_count,config),
      "kill_switch":kill_switch_gate(config),"emergency_stop":emergency_stop_gate(config),
      "account":account_gate(account),"buying_power":buying_power_gate(intent,config),
      "position":position_gate(intent,current_qty,config),"daily_loss":daily_loss_gate(realized_pnl,config),
      "exposure":exposure_gate(current_exposure,intent,config)}
    failed=[]
    for name,doc in checks.items():
        allowed=doc.get("allowed",doc.get("status")=="PASS")
        if not allowed: failed.append(name)
    d={"stage":"V84.34","status":"GATE_PASS" if not failed else "GATE_REJECTED",
       "checks":checks,"failed_checks":failed,"live_order_submission_authorized":False}
    d["preflight_sha256"]=hj(d);return d

def gate_receipt(intent,idem,preflight_doc):
    d={"stage":"V84.35","receipt_id":"live-gate-receipt-"+hj([intent,idem,preflight_doc])[:24],
       "status":preflight_doc["status"],"intent_id":intent["intent_id"],
       "idempotency_key":idem["key"],"failed_checks":preflight_doc["failed_checks"],
       "live_order_submission_authorized":False,"actual_order_submitted":False}
    d["receipt_sha256"]=hj(d);return d

def replay_guard(receipts):
    hashes=[x["receipt_sha256"] for x in receipts]
    duplicate=len(hashes)!=len(set(hashes))
    d={"stage":"V84.36","receipt_count":len(receipts),"replay_detected":duplicate,"accepted":not duplicate}
    d["replay_sha256"]=hj(d);return d

def build_scenarios(config):
    account={"status":"ACTIVE","equity":100000.0,"buying_power":config.buying_power,
             "trading_blocked":True,"source":"OFFLINE_FIXTURE"}
    cases=[
      (make_live_intent("AAPL","BUY",2,100),3,0,0.0,1000.0),
      (make_live_intent("MSFT","BUY",10,100),3,0,0.0,1000.0),
      (make_live_intent("SPY","SELL",10,100),3,5,0.0,1000.0),
      (make_live_intent("QQQ","BUY",2,400),2,0,-500.0,4800.0),
    ]
    rows=[]
    for i,(intent,approvals,current_qty,pnl,exposure) in enumerate(cases,1):
        idem=idempotency_key(intent);pf=preflight(intent,approvals,account,current_qty,pnl,exposure,config)
        receipt=gate_receipt(intent,idem,pf)
        rows.append({"scenario":i,"intent":intent,"idempotency":idem,"preflight":pf,"receipt":receipt})
    dup=duplicate_guard([rows[0]["idempotency"]["key"],rows[0]["idempotency"]["key"]])
    replay=replay_guard([rows[0]["receipt"],rows[0]["receipt"]])
    d={"stage":"V84.37","status":"PASS","scenario_count":len(rows),
       "gate_pass_count":sum(x["receipt"]["status"]=="GATE_PASS" for x in rows),
       "gate_reject_count":sum(x["receipt"]["status"]=="GATE_REJECTED" for x in rows),
       "duplicate_detected":dup["duplicate_detected"],"replay_detected":replay["replay_detected"],
       "rows":rows}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,policy,scenarios):
    checks={"policy_pass":policy["status"]=="PASS",
      "network_submission_false":policy["rules"]["network_submission_enabled"] is False,
      "live_submit_false":policy["rules"]["live_order_submit_enabled"] is False,
      "scenario_count_four":scenarios["scenario_count"]==4,
      "gate_pass_positive":scenarios["gate_pass_count"]>0,
      "gate_reject_positive":scenarios["gate_reject_count"]>0,
      "duplicate_detected":scenarios["duplicate_detected"],
      "replay_detected":scenarios["replay_detected"],
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.38","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="live-order-gate-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V84.39","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"live_order_gate_master_ledger_v84_39.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"live_order_gate_master_ledger_v84_39.json";b=lp.read_bytes()
    d={"stage":"V84.40","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"live_order_gate_manifest_v84_40.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"live_order_gate_master_ledger_v84_39.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_enablement_certificate(root/"release/v84_20/output/live_enablement_certificate_v84_20.json")
    policy=gate_policy();scenarios=build_scenarios(c);audit=build_audit(c,policy,scenarios)
    docs={"gate_policy":policy,"scenarios":scenarios,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"scenario_count":scenarios["scenario_count"],"gate_pass_count":scenarios["gate_pass_count"],
      "gate_reject_count":scenarios["gate_reject_count"],"duplicate_detected":scenarios["duplicate_detected"],
      "replay_detected":scenarios["replay_detected"],"audit_status":audit["status"],
      "source_live_enablement_complete":source["live_enablement_foundation_complete"]}
    return {"stage":"V84.40","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v84_20_certificate_present":(root/"release/v84_20/output/live_enablement_certificate_v84_20.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","scenario_count_four":s["scenario_count"]==4,
      "gate_pass_positive":s["gate_pass_count"]>0,"gate_reject_positive":s["gate_reject_count"]>0,
      "duplicate_detected":s["duplicate_detected"],"replay_detected":s["replay_detected"],
      "audit_pass":s["audit_status"]=="PASS","manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V84.40","status":status,"scope":"OFFLINE_LIVE_ORDER_GATE",
      "stages_completed":[f"V84.{i:02d}" for i in range(21,41)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"live_order_gate_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "live_order_gate_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "live_order_submission_authorized":False,"live_trading_authorized":False,
      "live_order_gate_complete":status=="PASS",
      "next_phase":"V84_41_LIVE_ORDER_AUTHORIZATION_FOUNDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"live_order_gate_certificate_v84_40.json",cert)
    wj(out/"live_order_gate_verify_v84_40.json",{"stage":"V84.40","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
