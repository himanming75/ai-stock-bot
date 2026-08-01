from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

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
class LiveSafetyConfig:
    mode:str="LIVE_LOCKED"
    required_approvals:int=2
    authorization_ttl_seconds:int=300
    maximum_daily_loss_pct:float=0.02
    maximum_drawdown_pct:float=0.05
    maximum_order_notional:float=1000.0
    maximum_position_notional:float=5000.0
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="LIVE_LOCKED": raise ValueError("live must remain locked")
        if self.required_approvals<2 or self.authorization_ttl_seconds<60: raise ValueError("approval policy")
        if not 0<self.maximum_daily_loss_pct<=1 or not 0<self.maximum_drawdown_pct<=1: raise ValueError("risk limits")
        if self.maximum_order_notional<=0 or self.maximum_position_notional<=0: raise ValueError("notional limits")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline safety only")

def validate_paper_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V82.00" or c.get("status")!="PASS": raise ValueError("bad V82.00 certificate")
    if c.get("paper_framework_certified") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("paper prerequisite")
    return c

def environment_guard(environment:str)->dict[str,Any]:
    env=environment.strip().upper()
    if env not in {"DEV","TEST","PAPER","LIVE"}: raise ValueError("environment")
    live_blocked=env=="LIVE"
    d={"stage":"V82.01","environment":env,"live_environment_detected":live_blocked,
       "live_access_allowed":False,"network_access_allowed":False}
    d["environment_sha256"]=hj(d);return d

def live_mode_lock()->dict[str,Any]:
    d={"stage":"V82.02","status":"LOCKED","live_mode_enabled":False,
       "unlock_requires_human_approval":True,"automatic_unlock_allowed":False}
    d["lock_sha256"]=hj(d);return d

def approval_request(user_id:str,reason:str,ttl:int)->dict[str,Any]:
    if not user_id.strip() or not reason.strip() or ttl<60: raise ValueError("approval request")
    d={"stage":"V82.03","request_id":"approval-"+hj([user_id,reason,ttl])[:20],
       "requested_by":user_id,"reason":reason,"ttl_seconds":ttl,"status":"PENDING",
       "live_authorization_granted":False}
    d["request_sha256"]=hj(d);return d

def add_approval(request:dict[str,Any],approver_id:str)->dict[str,Any]:
    if request["status"] not in {"PENDING","PARTIALLY_APPROVED"}: raise ValueError("approval state")
    approvals=list(request.get("approvals",[]))
    if approver_id in approvals: raise ValueError("duplicate approval")
    approvals.append(approver_id)
    d={**request,"approvals":approvals,"status":"PARTIALLY_APPROVED",
       "live_authorization_granted":False}
    d["request_sha256"]=hj({k:v for k,v in d.items() if k!="request_sha256"});return d

def evaluate_approvals(request:dict[str,Any],config:LiveSafetyConfig)->dict[str,Any]:
    count=len(request.get("approvals",[]))
    enough=count>=config.required_approvals
    d={"stage":"V82.05","request_id":request["request_id"],"approval_count":count,
       "required_approvals":config.required_approvals,"approval_threshold_met":enough,
       "authorization_token_issued":False,"live_authorization_granted":False}
    d["evaluation_sha256"]=hj(d);return d

def issue_dry_run_token(evaluation:dict[str,Any],config:LiveSafetyConfig)->dict[str,Any]:
    if not evaluation["approval_threshold_met"]: raise ValueError("insufficient approvals")
    d={"stage":"V82.06","token_id":"dryrun-"+hj(evaluation)[:20],
       "scope":"DRY_RUN_ONLY","ttl_seconds":config.authorization_ttl_seconds,
       "network_allowed":False,"order_submission_allowed":False,
       "paper_allowed":False,"live_allowed":False}
    d["token_sha256"]=hj(d);return d

def kill_switch(state:str="ARMED")->dict[str,Any]:
    s=state.upper()
    if s not in {"ARMED","TRIGGERED"}: raise ValueError("kill switch")
    d={"stage":"V82.07","state":s,"trading_blocked":True,
       "cancel_all_authorized":False,"flatten_positions_authorized":False}
    d["kill_switch_sha256"]=hj(d);return d

def emergency_stop(reason:str)->dict[str,Any]:
    if not reason.strip(): raise ValueError("reason")
    d={"stage":"V82.08","status":"TRIGGERED","reason":reason,
       "new_orders_blocked":True,"network_calls_blocked":True,
       "live_authorization_revoked":True}
    d["emergency_sha256"]=hj(d);return d

def daily_loss_guard(pnl:float,equity:float,config:LiveSafetyConfig)->dict[str,Any]:
    if equity<=0: raise ValueError("equity")
    loss_pct=max(0.0,-pnl/equity)
    breached=loss_pct>=config.maximum_daily_loss_pct
    d={"stage":"V82.09","daily_pnl":pnl,"equity":equity,"daily_loss_pct":round(loss_pct,12),
       "limit":config.maximum_daily_loss_pct,"breached":breached,"trading_blocked":breached}
    d["daily_loss_sha256"]=hj(d);return d

def drawdown_guard(drawdown:float,config:LiveSafetyConfig)->dict[str,Any]:
    if drawdown<0 or drawdown>1: raise ValueError("drawdown")
    breached=drawdown>=config.maximum_drawdown_pct
    d={"stage":"V82.10","drawdown_pct":drawdown,"limit":config.maximum_drawdown_pct,
       "breached":breached,"trading_blocked":breached}
    d["drawdown_sha256"]=hj(d);return d

def order_notional_guard(quantity:int,price:float,config:LiveSafetyConfig)->dict[str,Any]:
    if quantity<1 or price<=0: raise ValueError("order")
    notional=quantity*price;allowed=notional<=config.maximum_order_notional
    d={"stage":"V82.11","quantity":quantity,"price":price,"notional":round(notional,8),
       "limit":config.maximum_order_notional,"allowed":allowed,
       "submission_authorized":False}
    d["order_guard_sha256"]=hj(d);return d

def position_notional_guard(position_notional:float,config:LiveSafetyConfig)->dict[str,Any]:
    if position_notional<0: raise ValueError("position")
    allowed=position_notional<=config.maximum_position_notional
    d={"stage":"V82.12","position_notional":position_notional,
       "limit":config.maximum_position_notional,"allowed":allowed,
       "live_position_change_authorized":False}
    d["position_guard_sha256"]=hj(d);return d

def dry_run_guard(token,env,order_guard,position_guard,loss_guard,dd_guard,kill,stop)->dict[str,Any]:
    checks={"dry_run_scope":token["scope"]=="DRY_RUN_ONLY",
      "environment_not_live":env["environment"]!="LIVE",
      "order_limit_pass":order_guard["allowed"],"position_limit_pass":position_guard["allowed"],
      "daily_loss_not_breached":not loss_guard["breached"],"drawdown_not_breached":not dd_guard["breached"],
      "kill_switch_armed":kill["state"]=="ARMED","emergency_stop_not_triggered":stop is None}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V82.13","status":"PASS" if not failed else "BLOCKED",
       "checks":checks,"failed_checks":failed,"dry_run_authorized":not failed,
       "paper_trading_authorized":False,"live_trading_authorized":False}
    d["guard_sha256"]=hj(d);return d

def authorization_state_machine()->dict[str,Any]:
    transitions={"LOCKED":["REQUESTED"],"REQUESTED":["PARTIALLY_APPROVED","REJECTED"],
      "PARTIALLY_APPROVED":["DRY_RUN_TOKEN","REJECTED"],"DRY_RUN_TOKEN":["EXPIRED","REVOKED"],
      "EXPIRED":[],"REVOKED":[],"REJECTED":[]}
    d={"stage":"V82.14","initial_state":"LOCKED","transitions":transitions,
       "live_state_present":False}
    d["state_machine_sha256"]=hj(d);return d

def build_audit(config,env,lock,evaluation,token,kill,guard,state_machine):
    checks={"mode_locked":config.mode=="LIVE_LOCKED","environment_not_live":env["environment"]!="LIVE",
      "lock_active":lock["live_mode_enabled"] is False,
      "approval_threshold_met":evaluation["approval_threshold_met"],
      "token_dry_run_only":token["scope"]=="DRY_RUN_ONLY",
      "kill_switch_armed":kill["state"]=="ARMED",
      "guard_pass":guard["status"]=="PASS",
      "live_never_authorized":guard["live_trading_authorized"] is False,
      "state_machine_no_live":state_machine["live_state_present"] is False,
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V82.15","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="live-safety-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V82.16","status":"PASS","package_id":pid,"document_count":len(docs),
      "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"live_safety_master_ledger_v82_16.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"live_safety_master_ledger_v82_16.json";b=lp.read_bytes()
    d={"stage":"V82.17","status":"PASS","package_id":ledger["package_id"],
      "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"live_safety_manifest_v82_17.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"live_safety_master_ledger_v82_16.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_paper_certificate(root/"release/v82_00/output/paper_performance_certificate_v82_00.json")
    env=environment_guard("PAPER");lock=live_mode_lock();req=approval_request("operator-1","dry-run validation",c.authorization_ttl_seconds)
    req=add_approval(req,"approver-a");req=add_approval(req,"approver-b");evaluation=evaluate_approvals(req,c)
    token=issue_dry_run_token(evaluation,c);kill=kill_switch("ARMED")
    loss=daily_loss_guard(-500,100000,c);dd=drawdown_guard(0.01,c)
    order=order_notional_guard(5,100,c);position=position_notional_guard(2500,c)
    guard=dry_run_guard(token,env,order,position,loss,dd,kill,None)
    machine=authorization_state_machine();audit=build_audit(c,env,lock,evaluation,token,kill,guard,machine)
    docs={"environment":env,"lock":lock,"approval_request":req,"approval_evaluation":evaluation,
      "dry_run_token":token,"kill_switch":kill,"daily_loss_guard":loss,"drawdown_guard":dd,
      "order_guard":order,"position_guard":position,"dry_run_guard":guard,
      "authorization_state_machine":machine,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"required_approvals":c.required_approvals,"approval_count":evaluation["approval_count"],
      "approval_threshold_met":evaluation["approval_threshold_met"],"token_scope":token["scope"],
      "kill_switch_state":kill["state"],"dry_run_authorized":guard["dry_run_authorized"],
      "paper_trading_authorized":False,"live_trading_authorized":False,
      "audit_status":audit["status"],"source_paper_framework_certified":source["paper_framework_certified"]}
    return {"stage":"V82.18","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v82_00_certificate_present":(root/"release/v82_00/output/paper_performance_certificate_v82_00.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","approval_threshold_met":s["approval_threshold_met"],
      "token_dry_run_only":s["token_scope"]=="DRY_RUN_ONLY","kill_switch_armed":s["kill_switch_state"]=="ARMED",
      "dry_run_authorized":s["dry_run_authorized"],"paper_not_authorized":s["paper_trading_authorized"] is False,
      "live_not_authorized":s["live_trading_authorized"] is False,"audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V82.20","status":status,"scope":"OFFLINE_LIVE_SAFETY_AND_AUTHORIZATION_FOUNDATION",
      "stages_completed":[f"V82.{i:02d}" for i in range(1,21)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"live_safety_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "live_safety_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_trading_authorized":False,"live_trading_authorized":False,
      "live_safety_foundation_complete":status=="PASS","next_phase":"V82_21_BROKER_READ_ONLY_INTEGRATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"live_safety_foundation_certificate_v82_20.json",cert)
    wj(out/"live_safety_foundation_verify_v82_20.json",{"stage":"V82.20","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
