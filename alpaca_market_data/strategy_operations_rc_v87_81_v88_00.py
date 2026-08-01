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
class StrategyOperationsRCConfig:
    mode: str = "PAPER_STRATEGY_OPERATIONS_RELEASE_CANDIDATE"
    environment: str = "PAPER"
    source_release_candidate: str = "PAPER_STRATEGY_EXECUTION_RC1"
    release_candidate: str = "PAPER_STRATEGY_OPERATIONS_RC1"
    strategy_id: str = "SAFE_MOMENTUM_PREVIEW"
    scheduler_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    allow_network: bool = False
    daily_order_limit: int = 1
    daily_notional_limit: float = 500.0
    max_open_positions: int = 3
    session_ttl_seconds: int = 900
    health_stale_seconds: int = 120
    actual_orders_submitted: int = 0
    network_requests_executed: int = 0
    def validate(self):
        if self.mode != "PAPER_STRATEGY_OPERATIONS_RELEASE_CANDIDATE": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if self.source_release_candidate != "PAPER_STRATEGY_EXECUTION_RC1": raise ValueError("source rc")
        if self.release_candidate != "PAPER_STRATEGY_OPERATIONS_RC1": raise ValueError("target rc")
        if not self.strategy_id.strip(): raise ValueError("strategy")
        if self.daily_order_limit != 1 or self.daily_notional_limit <= 0 or self.max_open_positions < 1:
            raise ValueError("limits")
        if self.session_ttl_seconds < 300 or self.health_stale_seconds <= 0: raise ValueError("runtime")
        if self.scheduler_enabled or self.auto_execution_enabled or self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.allow_network or self.actual_orders_submitted != 0 or self.network_requests_executed != 0:
            raise ValueError("offline only")

def validate_source(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V87.80" or c.get("status")!="PASS":
        raise ValueError("bad V87.80 certificate")
    if c.get("paper_strategy_execution_rc1_ready") is not True:
        raise ValueError("strategy RC prerequisite")
    s=c.get("strategy_execution_final_summary",{})
    if s.get("release_candidate")!="PAPER_STRATEGY_EXECUTION_RC1":
        raise ValueError("unexpected source release candidate")
    if c.get("network_requests_executed")!=0 or c.get("actual_orders_submitted")!=0:
        raise ValueError("unsafe source")
    return c

def rc_policy(config):
    d={"stage":"V87.81","status":"PASS",
       "source_release_candidate":config.source_release_candidate,
       "release_candidate":config.release_candidate,
       "scheduler_enabled":False,"auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,"promotion_authorized":False}
    d["policy_sha256"]=hj(d);return d

def runtime_profile(config):
    d={"stage":"V87.82","strategy_id":config.strategy_id,
       "daily_order_limit":config.daily_order_limit,
       "daily_notional_limit":config.daily_notional_limit,
       "max_open_positions":config.max_open_positions,
       "session_ttl_seconds":config.session_ttl_seconds,
       "health_stale_seconds":config.health_stale_seconds,
       "runtime_mode":"MANUAL_OFFLINE_RC"}
    d["profile_sha256"]=hj(d);return d

def startup_check(config):
    checks={"scheduler_disabled":config.scheduler_enabled is False,
            "auto_execution_disabled":config.auto_execution_enabled is False,
            "paper_submit_false":config.paper_order_submission_authorized is False,
            "live_false":config.live_trading_authorized is False,
            "network_disabled":config.allow_network is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.83","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed,"startup_authorized":not failed}
    d["startup_sha256"]=hj(d);return d

def startup_manager(config,startup):
    if startup["status"]!="PASS": raise ValueError("startup")
    d={"stage":"V87.84","session_id":"strategy-ops-session-"+hj([asdict(config),startup])[:24],
       "status":"READY_NOT_STARTED","manual_start_required":True,
       "scheduler_enabled":False,"network_enabled":False,
       "order_submission_enabled":False}
    d["session_sha256"]=hj(d);return d

def health_monitor(config,session,last_heartbeat_age_seconds=30):
    checks={"session_present":bool(session.get("session_id")),
            "heartbeat_fresh":0<=last_heartbeat_age_seconds<=config.health_stale_seconds,
            "scheduler_disabled":session.get("scheduler_enabled") is False,
            "network_disabled":session.get("network_enabled") is False,
            "submission_disabled":session.get("order_submission_enabled") is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.85","status":"PASS" if not failed else "FAIL",
       "last_heartbeat_age_seconds":last_heartbeat_age_seconds,
       "checks":checks,"failed_checks":failed}
    d["health_sha256"]=hj(d);return d

def runtime_metrics(session,health):
    d={"stage":"V87.86","session_id":session["session_id"],
       "health_status":health["status"],"signals_received":0,
       "signals_approved":0,"previews_created":0,
       "orders_submitted":0,"network_requests":0,
       "queue_depth":0,"incident_count":0}
    d["metrics_sha256"]=hj(d);return d

def scheduler_plan(config):
    d={"stage":"V87.87","status":"PASS","timezone":"America/New_York",
       "market_open_event":"DISABLED_PREVIEW","market_close_event":"DISABLED_PREVIEW",
       "weekday_schedule":["MON","TUE","WED","THU","FRI"],
       "holiday_calendar_required":True,
       "scheduler_enabled":config.scheduler_enabled}
    d["scheduler_sha256"]=hj(d);return d

def daily_limit_guard(config,orders_used,notional_used,open_positions):
    checks={"orders_within_limit":0<=orders_used<=config.daily_order_limit,
            "notional_within_limit":0<=notional_used<=config.daily_notional_limit,
            "positions_within_limit":0<=open_positions<=config.max_open_positions}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.88","status":"PASS" if not failed else "FAIL",
       "orders_used":orders_used,"notional_used":notional_used,
       "open_positions":open_positions,"checks":checks,"failed_checks":failed}
    d["limit_sha256"]=hj(d);return d

def incident_policy():
    d={"stage":"V87.89","status":"PASS",
       "levels":["INFO","WARNING","CRITICAL"],
       "critical_actions":["STOP_SESSION","CLEAR_QUEUE","RELEASE_BUDGET","RELEASE_LOCK","ROLLBACK"],
       "automatic_order_action":False,"manual_ack_required":True}
    d["incident_policy_sha256"]=hj(d);return d

def incident_record(level,code,message):
    if level not in {"INFO","WARNING","CRITICAL"}: raise ValueError("level")
    d={"stage":"V87.90","incident_id":"strategy-ops-incident-"+hj([level,code,message])[:20],
       "level":level,"code":code,"message":message,
       "acknowledged":False,"resolved":False}
    d["incident_sha256"]=hj(d);return d

def recovery_plan(incident):
    critical=incident["level"]=="CRITICAL"
    d={"stage":"V87.91","status":"PASS",
       "incident_id":incident["incident_id"],
       "stop_session":critical,"clear_queue":critical,
       "release_budget":critical,"release_lock":critical,
       "rollback_required":critical,"network_enabled":False}
    d["recovery_sha256"]=hj(d);return d

def daily_report(config,metrics,health,limits,incident_count):
    d={"stage":"V87.92","status":"PASS",
       "strategy_id":config.strategy_id,
       "health_status":health["status"],
       "limit_status":limits["status"],
       "signals_received":metrics["signals_received"],
       "signals_approved":metrics["signals_approved"],
       "previews_created":metrics["previews_created"],
       "orders_submitted":metrics["orders_submitted"],
       "network_requests":metrics["network_requests"],
       "incident_count":incident_count}
    d["report_sha256"]=hj(d);return d

def shutdown_manager(session):
    d={**session,"stage":"V87.93","status":"STOPPED",
       "queue_cleared":True,"budget_released":True,
       "strategy_lock_released":True,"network_enabled":False,
       "order_submission_enabled":False}
    d["session_sha256"]=hj({k:v for k,v in d.items() if k!="session_sha256"});return d

def rollback_package():
    d={"stage":"V87.94","status":"PASS","rollback_target":"V87.80",
       "stop_session":True,"disable_scheduler":True,
       "disable_auto_execution":True,"disable_order_submission":True,
       "disable_network":True,"clear_queue":True,
       "release_budget":True,"release_strategy_lock":True,
       "preserve_audit_logs":True}
    d["rollback_sha256"]=hj(d);return d

def operations_scenario(config):
    startup=startup_check(config);session=startup_manager(config,startup)
    health=health_monitor(config,session,30);metrics=runtime_metrics(session,health)
    scheduler=scheduler_plan(config)
    limits_pass=daily_limit_guard(config,0,0.0,0)
    limits_fail=daily_limit_guard(config,2,1000.0,4)
    incident_policy_doc=incident_policy()
    incident=incident_record("CRITICAL","SIMULATED_STALE_HEARTBEAT","offline RC recovery test")
    recovery=recovery_plan(incident)
    report=daily_report(config,metrics,health,limits_pass,1)
    shutdown=shutdown_manager(session)
    rollback=rollback_package()
    d={"stage":"V87.95","status":"PASS",
       "startup_status":startup["status"],
       "session_status":session["status"],
       "health_status":health["status"],
       "scheduler_enabled":scheduler["scheduler_enabled"],
       "positive_limit_status":limits_pass["status"],
       "negative_limit_status":limits_fail["status"],
       "incident_policy_status":incident_policy_doc["status"],
       "critical_recovery_ready":recovery["rollback_required"],
       "daily_report_status":report["status"],
       "shutdown_status":shutdown["status"],
       "rollback_status":rollback["status"],
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{"startup":startup,"session":session,"health":health,
                    "metrics":metrics,"scheduler":scheduler,
                    "limits_pass":limits_pass,"limits_fail":limits_fail,
                    "incident_policy":incident_policy_doc,"incident":incident,
                    "recovery":recovery,"daily_report":report,
                    "shutdown":shutdown,"rollback":rollback}}
    d["scenario_sha256"]=hj(d);return d

def audit(config,scenario):
    checks={"startup_pass":scenario["startup_status"]=="PASS",
            "session_ready":scenario["session_status"]=="READY_NOT_STARTED",
            "health_pass":scenario["health_status"]=="PASS",
            "scheduler_disabled":scenario["scheduler_enabled"] is False,
            "positive_limit_pass":scenario["positive_limit_status"]=="PASS",
            "negative_limit_fail":scenario["negative_limit_status"]=="FAIL",
            "incident_policy_pass":scenario["incident_policy_status"]=="PASS",
            "critical_recovery_ready":scenario["critical_recovery_ready"],
            "daily_report_pass":scenario["daily_report_status"]=="PASS",
            "shutdown_stopped":scenario["shutdown_status"]=="STOPPED",
            "rollback_pass":scenario["rollback_status"]=="PASS",
            "auto_execution_false":config.auto_execution_enabled is False,
            "network_zero":scenario["network_requests_executed"]==0,
            "orders_zero":scenario["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.96","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def acceptance_test(config,scenario,audit_doc):
    checks={"source_rc_valid":config.source_release_candidate=="PAPER_STRATEGY_EXECUTION_RC1",
            "target_rc_valid":config.release_candidate=="PAPER_STRATEGY_OPERATIONS_RC1",
            "scenario_pass":scenario["status"]=="PASS",
            "audit_pass":audit_doc["status"]=="PASS",
            "scheduler_disabled":config.scheduler_enabled is False,
            "network_zero":scenario["network_requests_executed"]==0,
            "orders_zero":scenario["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.97","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed,
       "release_candidate":config.release_candidate,
       "accepted":not failed}
    d["acceptance_sha256"]=hj(d);return d

def store(out,docs):
    pid="strategy-ops-rc-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V87.98","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"strategy_operations_rc_ledger_v87_98.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"strategy_operations_rc_ledger_v87_98.json";b=p.read_bytes()
    d={"stage":"V87.99","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"strategy_operations_rc_manifest_v87_99.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_source(root/"release/v87_80/output/strategy_execution_final_certificate_v87_80.json")
    policy=rc_policy(c);profile=runtime_profile(c);scenario=operations_scenario(c)
    au=audit(c,scenario);acceptance=acceptance_test(c,scenario,au)
    docs={"source_certificate":{"certificate_sha256":source["certificate_sha256"],
                               "release_candidate":source["strategy_execution_final_summary"]["release_candidate"]},
          "rc_policy":policy,"runtime_profile":profile,
          "operations_scenario":scenario,"audit":au,"acceptance_test":acceptance}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    summary={"source_release_candidate":c.source_release_candidate,
             "release_candidate":c.release_candidate,
             "strategy_id":c.strategy_id,
             "startup_status":scenario["startup_status"],
             "health_status":scenario["health_status"],
             "scheduler_enabled":scenario["scheduler_enabled"],
             "positive_limit_status":scenario["positive_limit_status"],
             "negative_limit_status":scenario["negative_limit_status"],
             "incident_recovery_ready":scenario["critical_recovery_ready"],
             "daily_report_status":scenario["daily_report_status"],
             "shutdown_status":scenario["shutdown_status"],
             "rollback_status":scenario["rollback_status"],
             "audit_status":au["status"],
             "acceptance_status":acceptance["status"],
             "network_requests_executed":0,"actual_orders_submitted":0}
    return {"stage":"V88.00","status":"PASS" if acceptance["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "startup_pass":s["startup_status"]=="PASS",
            "health_pass":s["health_status"]=="PASS",
            "scheduler_disabled":s["scheduler_enabled"] is False,
            "positive_limit_pass":s["positive_limit_status"]=="PASS",
            "negative_limit_fail":s["negative_limit_status"]=="FAIL",
            "incident_recovery_ready":s["incident_recovery_ready"],
            "daily_report_pass":s["daily_report_status"]=="PASS",
            "shutdown_stopped":s["shutdown_status"]=="STOPPED",
            "rollback_pass":s["rollback_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "acceptance_pass":s["acceptance_status"]=="PASS",
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V88.00","status":status,
       "scope":"PAPER_STRATEGY_OPERATIONS_RELEASE_CANDIDATE",
       "stages_completed":[f"V87.{i:02d}" for i in range(81,100)]+["V88.00"],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "strategy_operations_rc_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "strategy_operations_rc_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "paper_strategy_operations_rc_complete":status=="PASS",
       "paper_strategy_operations_rc1_ready":status=="PASS",
       "scheduler_enabled":False,
       "auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "next_phase":"V88_01_PAPER_SCHEDULER_FOUNDATION"}
    d["certificate_sha256"]=hj(d);wj(out/"strategy_operations_rc_certificate_v88_00.json",d)
    wj(out/"strategy_operations_rc_verify_v88_00.json",
       {"stage":"V88.00","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
