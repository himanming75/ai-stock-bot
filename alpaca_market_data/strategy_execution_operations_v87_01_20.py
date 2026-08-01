from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class StrategyExecutionOperationsConfig:
    mode: str = "PAPER_STRATEGY_EXECUTION_OPERATIONS_FOUNDATION"
    environment: str = "PAPER"
    strategy_id: str = "SAFE_MOMENTUM_PREVIEW"
    allowed_symbols: tuple[str,...] = ("AAPL","MSFT","SPY")
    max_signal_age_seconds: int = 300
    min_confidence: float = 0.60
    daily_order_limit: int = 1
    daily_notional_limit: float = 500.0
    max_position_count: int = 3
    manual_approval_required: bool = True
    strategy_lock_required: bool = True
    session_resume_supported: bool = True
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    allow_network: bool = False
    actual_orders_submitted: int = 0
    def validate(self):
        if self.mode != "PAPER_STRATEGY_EXECUTION_OPERATIONS_FOUNDATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if not self.strategy_id.strip() or not self.allowed_symbols: raise ValueError("strategy")
        if self.max_signal_age_seconds <= 0 or not (0 < self.min_confidence <= 1): raise ValueError("signal policy")
        if self.daily_order_limit != 1 or self.daily_notional_limit <= 0 or self.max_position_count < 1: raise ValueError("limits")
        if not self.manual_approval_required or not self.strategy_lock_required or not self.session_resume_supported:
            raise ValueError("operations controls")
        if self.auto_execution_enabled or self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.allow_network or self.actual_orders_submitted != 0: raise ValueError("offline only")

def validate_source(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V87.00" or c.get("status")!="PASS":
        raise ValueError("bad V87.00 certificate")
    if c.get("paper_broker_operations_foundation_complete") is not True:
        raise ValueError("operations prerequisite")
    if c.get("paper_order_submission_authorized") is not False or c.get("live_trading_authorized") is not False:
        raise ValueError("unsafe source")
    return c

def strategy_policy(config):
    d={"stage":"V87.01","status":"PASS","strategy_id":config.strategy_id,
       "environment":config.environment,"allowed_symbols":list(config.allowed_symbols),
       "manual_approval_required":config.manual_approval_required,
       "auto_execution_enabled":False,"paper_order_submission_authorized":False,
       "live_trading_authorized":False}
    d["policy_sha256"]=hj(d);return d

def signal_intake(config,symbol,side,confidence,reference_price,age_seconds):
    if side not in {"buy","sell"}: raise ValueError("side")
    d={"stage":"V87.02","signal_id":"signal-"+hj([config.strategy_id,symbol,side,confidence,reference_price,age_seconds])[:24],
       "strategy_id":config.strategy_id,"symbol":symbol,"side":side,
       "confidence":float(confidence),"reference_price":float(reference_price),
       "age_seconds":int(age_seconds),"status":"RECEIVED"}
    d["signal_sha256"]=hj(d);return d

def signal_validation(config,signal):
    checks={"strategy_match":signal["strategy_id"]==config.strategy_id,
            "symbol_allowed":signal["symbol"] in config.allowed_symbols,
            "side_valid":signal["side"] in {"buy","sell"},
            "confidence_valid":signal["confidence"]>=config.min_confidence,
            "age_valid":0<=signal["age_seconds"]<=config.max_signal_age_seconds,
            "price_positive":signal["reference_price"]>0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.03","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["validation_sha256"]=hj(d);return d

def risk_decision(config,signal,validation,current_positions,daily_orders_used,daily_notional_used):
    estimated_notional=signal["reference_price"]
    checks={"validation_pass":validation["status"]=="PASS",
            "position_limit":current_positions < config.max_position_count,
            "daily_order_budget":daily_orders_used < config.daily_order_limit,
            "daily_notional_budget":daily_notional_used + estimated_notional <= config.daily_notional_limit,
            "single_unit_preview":True}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.04","status":"PASS" if not failed else "REJECT",
       "checks":checks,"failed_checks":failed,
       "estimated_notional":estimated_notional,"quantity":1}
    d["risk_sha256"]=hj(d);return d

def strategy_lock(config,signal):
    if not config.strategy_lock_required: raise ValueError("lock required")
    d={"stage":"V87.05","lock_id":"strategy-lock-"+hj(signal)[:24],
       "strategy_id":config.strategy_id,"signal_id":signal["signal_id"],
       "status":"ACQUIRED","exclusive":True,"released":False}
    d["lock_sha256"]=hj(d);return d

def approval_request(config,signal,risk):
    if risk["status"]!="PASS": raise ValueError("risk rejection")
    d={"stage":"V87.06","approval_id":"manual-approval-"+hj([signal,risk])[:24],
       "signal_id":signal["signal_id"],"required":config.manual_approval_required,
       "status":"PENDING","approver_count":0,"required_approvers":1}
    d["approval_sha256"]=hj(d);return d

def approve(request,approver_id):
    if request["status"]!="PENDING" or not approver_id.strip(): raise ValueError("approval")
    d={**request,"stage":"V87.07","status":"APPROVED","approver_count":1,
       "approver_id":approver_id}
    d["approval_sha256"]=hj({k:v for k,v in d.items() if k!="approval_sha256"});return d

def execution_preview(signal,risk,approval):
    if approval["status"]!="APPROVED": raise ValueError("approval required")
    payload={"symbol":signal["symbol"],"qty":"1","side":signal["side"],
             "type":"market","time_in_force":"day"}
    d={"stage":"V87.08","preview_id":"execution-preview-"+hj([signal,risk,approval])[:24],
       "payload":payload,"estimated_notional":risk["estimated_notional"],
       "network_request_ready":False,"order_submission_ready":False,
       "status":"PREVIEW_ONLY"}
    d["preview_sha256"]=hj(d);return d

def budget_reservation(config,preview,daily_orders_used,daily_notional_used):
    next_orders=daily_orders_used+1;next_notional=daily_notional_used+preview["estimated_notional"]
    checks={"order_budget":next_orders<=config.daily_order_limit,
            "notional_budget":next_notional<=config.daily_notional_limit}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.09","status":"RESERVED" if not failed else "REJECTED",
       "checks":checks,"failed_checks":failed,"reserved_orders":1,
       "reserved_notional":preview["estimated_notional"],
       "next_daily_orders_used":next_orders,
       "next_daily_notional_used":next_notional}
    d["reservation_sha256"]=hj(d);return d

def execution_context(config,signal,lock,approval,preview,reservation):
    if reservation["status"]!="RESERVED": raise ValueError("budget")
    d={"stage":"V87.10","context_id":"execution-context-"+hj([signal,lock,approval,preview,reservation])[:24],
       "strategy_id":config.strategy_id,"signal_id":signal["signal_id"],
       "lock_id":lock["lock_id"],"approval_id":approval["approval_id"],
       "preview_id":preview["preview_id"],"status":"READY_FOR_MANUAL_REVIEW",
       "network_enabled":False,"order_submission_enabled":False}
    d["context_sha256"]=hj(d);return d

def execution_queue(context):
    d={"stage":"V87.11","queue_id":"strategy-queue-"+hj(context)[:24],
       "item_count":1,"items":[{"context_id":context["context_id"],"status":"QUEUED_PREVIEW"}],
       "dispatch_enabled":False}
    d["queue_sha256"]=hj(d);return d

def session_checkpoint(context,queue,reservation):
    d={"stage":"V87.12","checkpoint_id":"strategy-checkpoint-"+hj([context,queue,reservation])[:24],
       "context_id":context["context_id"],"queue_id":queue["queue_id"],
       "reserved_orders":reservation["reserved_orders"],
       "reserved_notional":reservation["reserved_notional"],
       "status":"SAVED","resumable":True}
    d["checkpoint_sha256"]=hj(d);return d

def resume_session(checkpoint):
    if not checkpoint.get("resumable"): raise ValueError("not resumable")
    d={"stage":"V87.13","resume_id":"strategy-resume-"+hj(checkpoint)[:24],
       "checkpoint_id":checkpoint["checkpoint_id"],"status":"RESUMED_PREVIEW_ONLY",
       "network_enabled":False,"dispatch_enabled":False}
    d["resume_sha256"]=hj(d);return d

def cancel_preview(context,reservation):
    d={"stage":"V87.14","context_id":context["context_id"],"status":"CANCELED",
       "budget_released":True,"released_orders":reservation["reserved_orders"],
       "released_notional":reservation["reserved_notional"],
       "network_requests_executed":0,"actual_orders_submitted":0}
    d["cancel_sha256"]=hj(d);return d

def release_lock(lock):
    if lock["released"]: raise ValueError("already released")
    d={**lock,"stage":"V87.15","status":"RELEASED","released":True}
    d["lock_sha256"]=hj({k:v for k,v in d.items() if k!="lock_sha256"});return d

def rejection_scenarios(config):
    scenarios=[]
    inputs=[
      ("BAD_SYMBOL","TSLA","buy",0.9,200,10,0,0,0),
      ("LOW_CONFIDENCE","AAPL","buy",0.2,200,10,0,0,0),
      ("STALE_SIGNAL","AAPL","buy",0.9,200,999,0,0,0),
      ("ORDER_LIMIT","AAPL","buy",0.9,200,10,0,1,0),
      ("NOTIONAL_LIMIT","AAPL","buy",0.9,600,10,0,0,0),
    ]
    for name,symbol,side,conf,price,age,pos,orders,notional in inputs:
        sig=signal_intake(config,symbol,side,conf,price,age)
        val=signal_validation(config,sig)
        risk=risk_decision(config,sig,val,pos,orders,notional)
        scenarios.append({"name":name,"validation_status":val["status"],"risk_status":risk["status"]})
    d={"stage":"V87.16","scenario_count":len(scenarios),
       "reject_count":sum(1 for s in scenarios if s["validation_status"]=="FAIL" or s["risk_status"]=="REJECT"),
       "scenarios":scenarios}
    d["scenarios_sha256"]=hj(d);return d

def rollback_plan():
    d={"stage":"V87.17","status":"PASS","rollback_target":"V87.00",
       "cancel_preview":True,"release_budget":True,"release_strategy_lock":True,
       "clear_execution_queue":True,"disable_dispatch":True,
       "disable_network":True,"disable_order_submission":True}
    d["rollback_sha256"]=hj(d);return d

def operations_scenario(config):
    signal=signal_intake(config,"AAPL","buy",0.85,200.0,30)
    validation=signal_validation(config,signal)
    risk=risk_decision(config,signal,validation,0,0,0.0)
    lock=strategy_lock(config,signal)
    request=approval_request(config,signal,risk)
    approval=approve(request,"operator-1")
    preview=execution_preview(signal,risk,approval)
    reservation=budget_reservation(config,preview,0,0.0)
    context=execution_context(config,signal,lock,approval,preview,reservation)
    queue=execution_queue(context)
    checkpoint=session_checkpoint(context,queue,reservation)
    resumed=resume_session(checkpoint)
    canceled=cancel_preview(context,reservation)
    released=release_lock(lock)
    rejects=rejection_scenarios(config)
    d={"stage":"V87.18","status":"PASS",
       "signal_validation_status":validation["status"],
       "risk_status":risk["status"],"approval_status":approval["status"],
       "preview_status":preview["status"],"reservation_status":reservation["status"],
       "context_status":context["status"],"queue_dispatch_enabled":queue["dispatch_enabled"],
       "checkpoint_resumable":checkpoint["resumable"],"resume_status":resumed["status"],
       "preview_canceled":canceled["status"]=="CANCELED",
       "lock_released":released["released"],"rejection_count":rejects["reject_count"],
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{"signal":signal,"validation":validation,"risk":risk,"lock":lock,
                    "approval_request":request,"approval":approval,"preview":preview,
                    "reservation":reservation,"context":context,"queue":queue,
                    "checkpoint":checkpoint,"resumed":resumed,"canceled":canceled,
                    "released_lock":released,"rejections":rejects}}
    d["scenario_sha256"]=hj(d);return d

def audit(config,scenario,rollback):
    checks={"validation_pass":scenario["signal_validation_status"]=="PASS",
            "risk_pass":scenario["risk_status"]=="PASS",
            "approval_pass":scenario["approval_status"]=="APPROVED",
            "preview_only":scenario["preview_status"]=="PREVIEW_ONLY",
            "reservation_created":scenario["reservation_status"]=="RESERVED",
            "context_ready":scenario["context_status"]=="READY_FOR_MANUAL_REVIEW",
            "dispatch_disabled":scenario["queue_dispatch_enabled"] is False,
            "checkpoint_resumable":scenario["checkpoint_resumable"],
            "resume_preview_only":scenario["resume_status"]=="RESUMED_PREVIEW_ONLY",
            "preview_canceled":scenario["preview_canceled"],
            "lock_released":scenario["lock_released"],
            "rejections_positive":scenario["rejection_count"]>=5,
            "rollback_pass":rollback["status"]=="PASS",
            "auto_execution_false":config.auto_execution_enabled is False,
            "network_zero":scenario["network_requests_executed"]==0,
            "orders_zero":scenario["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.19","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store(out,docs):
    pid="strategy-exec-ops-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V87.19","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"strategy_execution_ledger_v87_19.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"strategy_execution_ledger_v87_19.json";b=p.read_bytes()
    d={"stage":"V87.20","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"strategy_execution_manifest_v87_20.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_source(root/"release/v87_00/output/operations_certificate_v87_00.json")
    policy=strategy_policy(c);scenario=operations_scenario(c);rollback=rollback_plan()
    au=audit(c,scenario,rollback)
    docs={"source_certificate":{"certificate_sha256":source["certificate_sha256"],
                               "release_candidate":source["operations_summary"]["release_candidate"]},
          "strategy_policy":policy,"operations_scenario":scenario,
          "rollback_plan":rollback,"audit":au}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    summary={"strategy_id":c.strategy_id,
             "allowed_symbol_count":len(c.allowed_symbols),
             "signal_validation_status":scenario["signal_validation_status"],
             "risk_status":scenario["risk_status"],
             "approval_status":scenario["approval_status"],
             "preview_status":scenario["preview_status"],
             "reservation_status":scenario["reservation_status"],
             "context_status":scenario["context_status"],
             "checkpoint_resumable":scenario["checkpoint_resumable"],
             "session_resume_status":scenario["resume_status"],
             "preview_canceled":scenario["preview_canceled"],
             "strategy_lock_released":scenario["lock_released"],
             "rejection_count":scenario["rejection_count"],
             "rollback_status":rollback["status"],
             "audit_status":au["status"],
             "network_requests_executed":0,
             "actual_orders_submitted":0}
    return {"stage":"V87.20","status":"PASS" if au["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "signal_validation_pass":s["signal_validation_status"]=="PASS",
            "risk_pass":s["risk_status"]=="PASS",
            "approval_approved":s["approval_status"]=="APPROVED",
            "preview_only":s["preview_status"]=="PREVIEW_ONLY",
            "budget_reserved":s["reservation_status"]=="RESERVED",
            "context_ready":s["context_status"]=="READY_FOR_MANUAL_REVIEW",
            "checkpoint_resumable":s["checkpoint_resumable"],
            "session_resumed":s["session_resume_status"]=="RESUMED_PREVIEW_ONLY",
            "preview_canceled":s["preview_canceled"],
            "lock_released":s["strategy_lock_released"],
            "rejection_count_valid":s["rejection_count"]>=5,
            "rollback_pass":s["rollback_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V87.20","status":status,
       "scope":"PAPER_STRATEGY_EXECUTION_OPERATIONS_FOUNDATION",
       "stages_completed":[f"V87.{i:02d}" for i in range(1,21)],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "strategy_execution_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "strategy_execution_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "paper_strategy_execution_operations_complete":status=="PASS",
       "strategy_execution_preview_ready":status=="PASS",
       "auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,
       "actual_orders_submitted":0,
       "next_phase":"V87_21_PAPER_STRATEGY_EXECUTION_SIMULATION"}
    d["certificate_sha256"]=hj(d);wj(out/"strategy_execution_certificate_v87_20.json",d)
    wj(out/"strategy_execution_verify_v87_20.json",
       {"stage":"V87.20","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
