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
class LiveBrokerEnablementConfig:
    mode:str="LIVE_BROKER_ENABLEMENT_OFFLINE"
    environment:str="LIVE"
    required_approvals:int=3
    max_order_notional:float=500.0
    max_position_notional:float=2500.0
    max_daily_loss:float=250.0
    kill_switch_armed:bool=True
    emergency_stop_enabled:bool=True
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="LIVE_BROKER_ENABLEMENT_OFFLINE": raise ValueError("safe mode")
        if self.environment!="LIVE": raise ValueError("live environment contract")
        if self.required_approvals<3: raise ValueError("approval threshold")
        if min(self.max_order_notional,self.max_position_notional,self.max_daily_loss)<=0: raise ValueError("risk limits")
        if not self.kill_switch_armed or not self.emergency_stop_enabled: raise ValueError("safety controls")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline enablement only")

def validate_paper_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V84.00" or c.get("status")!="PASS": raise ValueError("bad V84.00 certificate")
    if c.get("paper_broker_framework_complete") is not True or c.get("paper_framework_certified") is not True:
        raise ValueError("paper prerequisite")
    if c.get("live_trading_authorized") is not False or c.get("actual_orders_submitted")!=0:
        raise ValueError("unsafe prerequisite")
    return c

def capability_registry():
    caps={
      "live_account_read":True,"live_positions_read":True,"live_orders_read":True,"live_fills_read":True,
      "live_clock_read":True,"live_order_preview":True,
      "live_order_submit":False,"live_order_cancel":False,"live_order_replace":False,
      "credential_load":False,"network_connect":False,
    }
    d={"stage":"V84.01","status":"PASS","capabilities":caps,
       "read_capability_count":sum(v for k,v in caps.items() if k.endswith("_read")),
       "preview_capability_count":1 if caps["live_order_preview"] else 0,
       "write_capability_count":sum(v for k,v in caps.items() if "submit" in k or "cancel" in k or "replace" in k),
       "network_capability_count":1 if caps["network_connect"] else 0,
       "credential_capability_count":1 if caps["credential_load"] else 0}
    d["registry_sha256"]=hj(d);return d

def environment_guard(environment):
    env=environment.upper()
    d={"stage":"V84.02","environment":env,"live_environment_selected":env=="LIVE",
       "paper_environment_allowed":False,"environment_switch_allowed":False,
       "network_activation_allowed":False}
    d["environment_sha256"]=hj(d);return d

def approval_request(operator_id,reason):
    if not operator_id.strip() or not reason.strip(): raise ValueError("request")
    d={"stage":"V84.03","request_id":"live-enable-"+hj([operator_id,reason])[:20],
       "operator_id":operator_id,"reason":reason,"status":"PENDING",
       "live_trading_authorized":False}
    d["request_sha256"]=hj(d);return d

def add_approval(request,approver):
    approvals=list(request.get("approvals",[]))
    if approver in approvals: raise ValueError("duplicate approval")
    approvals.append(approver)
    d={**request,"stage":"V84.04","approvals":approvals,"status":"PARTIALLY_APPROVED",
       "live_trading_authorized":False}
    d["request_sha256"]=hj({k:v for k,v in d.items() if k!="request_sha256"});return d

def evaluate_approvals(request,config):
    count=len(request.get("approvals",[]));met=count>=config.required_approvals
    d={"stage":"V84.05","approval_count":count,"required_approvals":config.required_approvals,
       "threshold_met":met,"enablement_review_ready":met,
       "live_trading_authorized":False}
    d["approval_sha256"]=hj(d);return d

def kill_switch(config):
    d={"stage":"V84.06","state":"ARMED" if config.kill_switch_armed else "DISARMED",
       "armed":config.kill_switch_armed,"blocks_submission":True,
       "manual_disarm_required":True}
    d["kill_switch_sha256"]=hj(d);return d

def emergency_stop(config):
    d={"stage":"V84.07","enabled":config.emergency_stop_enabled,"state":"READY",
       "can_halt":True,"network_halt_supported":False,
       "actual_submission_halt_count":0}
    d["emergency_sha256"]=hj(d);return d

def account_guard(account):
    checks={"status_active":account["status"]=="ACTIVE","equity_positive":account["equity"]>0,
      "buying_power_positive":account["buying_power"]>0,"trading_blocked":account["trading_blocked"] is True,
      "fixture_source":account["source"]=="OFFLINE_FIXTURE"}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.08","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
       "account":account}
    d["account_guard_sha256"]=hj(d);return d

def position_guard(position,config):
    notional=abs(position["quantity"]*position["mark_price"])
    allowed=notional<=config.max_position_notional
    d={"stage":"V84.09","symbol":position["symbol"],"notional":round(notional,8),
       "limit":config.max_position_notional,"allowed":allowed}
    d["position_guard_sha256"]=hj(d);return d

def order_guard(order,config):
    notional=order["quantity"]*order["reference_price"]
    allowed=notional<=config.max_order_notional
    d={"stage":"V84.10","symbol":order["symbol"],"notional":round(notional,8),
       "limit":config.max_order_notional,"allowed":allowed,
       "submission_authorized":False}
    d["order_guard_sha256"]=hj(d);return d

def daily_loss_guard(realized_pnl,config):
    loss=max(0.0,-realized_pnl);allowed=loss<=config.max_daily_loss
    d={"stage":"V84.11","realized_pnl":realized_pnl,"daily_loss":loss,
       "loss_limit":config.max_daily_loss,"allowed":allowed,
       "halt_required":not allowed}
    d["daily_loss_sha256"]=hj(d);return d

def session_validator(env,approval,ks,emergency,account):
    checks={"live_environment_selected":env["live_environment_selected"],
      "approval_threshold_met":approval["threshold_met"],
      "kill_switch_armed":ks["armed"],
      "emergency_stop_ready":emergency["enabled"],
      "account_guard_pass":account["status"]=="PASS"}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.12","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
       "live_session_ready_for_review":not failed,
       "live_trading_authorized":False}
    d["session_sha256"]=hj(d);return d

def permission_receipt(session,registry):
    checks={"session_pass":session["status"]=="PASS","write_capabilities_zero":registry["write_capability_count"]==0,
      "network_capabilities_zero":registry["network_capability_count"]==0,
      "credential_capabilities_zero":registry["credential_capability_count"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.13","receipt_id":"live-foundation-"+hj([session,registry])[:24],
       "status":"FOUNDATION_READY" if not failed else "DENIED","checks":checks,"failed_checks":failed,
       "scope":"LIVE_ENABLEMENT_REVIEW_ONLY","live_trading_authorized":False}
    d["receipt_sha256"]=hj(d);return d

def state_machine():
    transitions={"LOCKED":["REQUESTED"],"REQUESTED":["PARTIALLY_APPROVED","DENIED"],
      "PARTIALLY_APPROVED":["FOUNDATION_READY","DENIED"],"FOUNDATION_READY":["REVOKED","EXPIRED"],
      "REVOKED":[],"EXPIRED":[],"DENIED":[]}
    d={"stage":"V84.14","initial_state":"LOCKED","transitions":transitions,
       "live_enabled_state_present":False,"order_submit_state_present":False}
    d["state_machine_sha256"]=hj(d);return d

def build_scenarios(config):
    account={"account_id":"live-fixture","status":"ACTIVE","equity":100000.0,
             "buying_power":50000.0,"trading_blocked":True,"source":"OFFLINE_FIXTURE"}
    ag=account_guard(account)
    pg_ok=position_guard({"symbol":"AAPL","quantity":5,"mark_price":100.0},config)
    pg_bad=position_guard({"symbol":"MSFT","quantity":20,"mark_price":200.0},config)
    og_ok=order_guard({"symbol":"AAPL","quantity":2,"reference_price":100.0},config)
    og_bad=order_guard({"symbol":"SPY","quantity":2,"reference_price":500.0},config)
    loss_ok=daily_loss_guard(-100.0,config);loss_bad=daily_loss_guard(-500.0,config)
    d={"stage":"V84.15","status":"PASS","account_guard_status":ag["status"],
       "position_pass_count":sum(x["allowed"] for x in [pg_ok,pg_bad]),
       "position_reject_count":sum(not x["allowed"] for x in [pg_ok,pg_bad]),
       "order_pass_count":sum(x["allowed"] for x in [og_ok,og_bad]),
       "order_reject_count":sum(not x["allowed"] for x in [og_ok,og_bad]),
       "daily_loss_pass_count":sum(x["allowed"] for x in [loss_ok,loss_bad]),
       "daily_loss_halt_count":sum(x["halt_required"] for x in [loss_ok,loss_bad]),
       "documents":{"account":ag,"position_ok":pg_ok,"position_bad":pg_bad,
         "order_ok":og_ok,"order_bad":og_bad,"loss_ok":loss_ok,"loss_bad":loss_bad}}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,registry,env,approval,ks,emergency,session,receipt,machine,scenarios):
    checks={"registry_pass":registry["status"]=="PASS","write_capabilities_zero":registry["write_capability_count"]==0,
      "network_capabilities_zero":registry["network_capability_count"]==0,
      "credential_capabilities_zero":registry["credential_capability_count"]==0,
      "environment_live":env["live_environment_selected"],"approval_threshold_met":approval["threshold_met"],
      "kill_switch_armed":ks["armed"],"emergency_stop_ready":emergency["enabled"],
      "session_pass":session["status"]=="PASS","receipt_ready":receipt["status"]=="FOUNDATION_READY",
      "state_machine_no_live":machine["live_enabled_state_present"] is False,
      "state_machine_no_submit":machine["order_submit_state_present"] is False,
      "position_pass_and_reject":scenarios["position_pass_count"]>0 and scenarios["position_reject_count"]>0,
      "order_pass_and_reject":scenarios["order_pass_count"]>0 and scenarios["order_reject_count"]>0,
      "loss_pass_and_halt":scenarios["daily_loss_pass_count"]>0 and scenarios["daily_loss_halt_count"]>0,
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.16","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="live-enablement-foundation-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V84.17","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"live_enablement_master_ledger_v84_17.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"live_enablement_master_ledger_v84_17.json";b=lp.read_bytes()
    d={"stage":"V84.18","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"live_enablement_manifest_v84_18.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"live_enablement_master_ledger_v84_17.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_paper_certificate(root/"release/v84_00/output/paper_broker_final_certificate_v84_00.json")
    registry=capability_registry();env=environment_guard(c.environment)
    req=approval_request("operator-1","live foundation review")
    req=add_approval(req,"approver-a");req=add_approval(req,"approver-b");req=add_approval(req,"approver-c")
    approval=evaluate_approvals(req,c);ks=kill_switch(c);emergency=emergency_stop(c)
    account=account_guard({"account_id":"live-fixture","status":"ACTIVE","equity":100000.0,
      "buying_power":50000.0,"trading_blocked":True,"source":"OFFLINE_FIXTURE"})
    session=session_validator(env,approval,ks,emergency,account)
    receipt=permission_receipt(session,registry);machine=state_machine();scenarios=build_scenarios(c)
    audit=build_audit(c,registry,env,approval,ks,emergency,session,receipt,machine,scenarios)
    docs={"capability_registry":registry,"environment_guard":env,"approval_request":req,
      "approval_evaluation":approval,"kill_switch":ks,"emergency_stop":emergency,
      "account_guard":account,"session_validator":session,"permission_receipt":receipt,
      "state_machine":machine,"scenarios":scenarios,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"capability_count":len(registry["capabilities"]),"read_capability_count":registry["read_capability_count"],
      "write_capability_count":registry["write_capability_count"],"network_capability_count":registry["network_capability_count"],
      "credential_capability_count":registry["credential_capability_count"],
      "approval_count":approval["approval_count"],"required_approvals":approval["required_approvals"],
      "approval_threshold_met":approval["threshold_met"],"kill_switch_state":ks["state"],
      "emergency_stop_state":emergency["state"],"session_status":session["status"],
      "permission_receipt_status":receipt["status"],"audit_status":audit["status"],
      "source_paper_framework_complete":source["paper_broker_framework_complete"]}
    return {"stage":"V84.19","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v84_00_certificate_present":(root/"release/v84_00/output/paper_broker_final_certificate_v84_00.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","capabilities_positive":s["capability_count"]>0,
      "write_capabilities_zero":s["write_capability_count"]==0,"network_capabilities_zero":s["network_capability_count"]==0,
      "credential_capabilities_zero":s["credential_capability_count"]==0,
      "approval_threshold_met":s["approval_threshold_met"],"kill_switch_armed":s["kill_switch_state"]=="ARMED",
      "emergency_stop_ready":s["emergency_stop_state"]=="READY","session_pass":s["session_status"]=="PASS",
      "receipt_ready":s["permission_receipt_status"]=="FOUNDATION_READY","audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V84.20","status":status,"scope":"OFFLINE_LIVE_BROKER_ENABLEMENT_FOUNDATION",
      "stages_completed":[f"V84.{i:02d}" for i in range(1,21)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"live_enablement_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "live_enablement_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_trading_authorized":False,"live_trading_authorized":False,
      "live_order_submission_authorized":False,
      "live_enablement_foundation_complete":status=="PASS",
      "next_phase":"V84_21_LIVE_ORDER_GATE"}
    cert["certificate_sha256"]=hj(cert);wj(out/"live_enablement_certificate_v84_20.json",cert)
    wj(out/"live_enablement_verify_v84_20.json",{"stage":"V84.20","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
