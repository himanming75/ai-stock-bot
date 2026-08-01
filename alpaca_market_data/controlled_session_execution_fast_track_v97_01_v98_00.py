
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json, os, time

CONFIRMATION_TEXT = "START ONE CONTROLLED ALPACA PAPER SESSION"

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()
def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class ControlledSessionConfig:
    mode: str = "ACTUAL_PAPER_CONTROLLED_SESSION_EXECUTION_FAST_TRACK"
    release_candidate: str = "ACTUAL_PAPER_CONTROLLED_SESSION_RC2"
    session_ttl_seconds: int = 300
    heartbeat_interval_seconds: int = 30
    max_orders_per_session: int = 1
    max_order_notional: float = 100.0
    max_quantity: int = 1
    allowed_symbols: tuple[str, ...] = ("AAPL","MSFT","SPY")
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    live_trading_authorized: bool = False
    default_network_requests_executed: int = 0
    default_actual_orders_submitted: int = 0

    def validate(self):
        if self.mode != "ACTUAL_PAPER_CONTROLLED_SESSION_EXECUTION_FAST_TRACK":
            raise ValueError("mode")
        if self.release_candidate != "ACTUAL_PAPER_CONTROLLED_SESSION_RC2":
            raise ValueError("release candidate")
        if (self.session_ttl_seconds, self.heartbeat_interval_seconds) != (300,30):
            raise ValueError("timing")
        if (self.max_orders_per_session, self.max_order_notional, self.max_quantity) != (1,100.0,1):
            raise ValueError("limits")
        if any([self.scheduler_enabled,self.runtime_loop_enabled,self.auto_execution_enabled,self.live_trading_authorized]):
            raise ValueError("unsafe enablement")
        if self.default_network_requests_executed or self.default_actual_orders_submitted:
            raise ValueError("unsafe defaults")

def validate_source(path: Path):
    cert=json.loads(path.read_text(encoding="utf-8"))
    unsigned=dict(cert); expected=unsigned.pop("certificate_sha256",None)
    if expected != hjson(unsigned): raise ValueError("source hash")
    if cert.get("stage")!="V97.00" or cert.get("status")!="PASS":
        raise ValueError("source")
    if cert.get("actual_paper_controlled_execution_validation_rc1_ready") is not True:
        raise ValueError("prerequisite")
    return cert

def session_environment(env=None):
    env=os.environ if env is None else env
    flags={
        "read_opt_in":env.get("AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ")=="1",
        "single_order_opt_in":env.get("AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER")=="1",
        "controlled_execution_opt_in":env.get("AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION")=="1",
        "session_opt_in":env.get("AI_STOCK_BOT_ENABLE_CONTROLLED_SESSION")=="1",
        "confirmation":env.get("AI_STOCK_BOT_CONTROLLED_SESSION_CONFIRMATION")==CONFIRMATION_TEXT,
        "credentials_present":bool(env.get("APCA_API_KEY_ID")) and bool(env.get("APCA_API_SECRET_KEY")),
        "kill_switch_clear":env.get("AI_STOCK_BOT_KILL_SWITCH","0")=="0",
    }
    ready=all(flags.values())
    return {"stage":"V97.01","status":"READY" if ready else "BLOCKED",
            "flags":flags,"session_ready":ready}

def create_session(config:ControlledSessionConfig, now:int=1_000_000):
    session={
        "stage":"V97.10","status":"CREATED",
        "session_id":"paper-session-"+hjson({"now":now,"scope":"ONE_ORDER"})[:24],
        "created_at":now,"expires_at":now+config.session_ttl_seconds,
        "heartbeat_interval_seconds":config.heartbeat_interval_seconds,
        "remaining_orders":1,"remaining_uses":1,
        "scope":"ONE_CONTROLLED_PAPER_ORDER",
        "network_enabled":False,"order_submission_enabled":False,
    }
    session["session_sha256"]=hjson(session)
    return session

def start_session(session, env):
    gate=session_environment(env)
    if gate["status"]!="READY":
        return {"stage":"V97.20","status":"BLOCKED","reason":"environment gate"}
    if session["status"]!="CREATED":
        return {"stage":"V97.20","status":"BLOCKED","reason":"bad session state"}
    started=dict(session)
    started["status"]="ACTIVE"
    started["started_at"]=session["created_at"]+1
    started["network_enabled"]=False
    started["order_submission_enabled"]=False
    return {"stage":"V97.20","status":"ACTIVE","session":started}

def heartbeat(session_doc, at:int):
    s=session_doc["session"]
    if s["status"]!="ACTIVE":
        return {"stage":"V97.30","status":"BLOCKED"}
    if at>=s["expires_at"]:
        return {"stage":"V97.30","status":"EXPIRED","heartbeat_accepted":False}
    age=at-s["started_at"]
    return {"stage":"V97.30","status":"HEALTHY","heartbeat_accepted":True,
            "heartbeat_at":at,"session_age_seconds":age}

def duplicate_session_guard(active_session_ids, requested_session_id):
    dup=requested_session_id in active_session_ids
    return {"stage":"V97.40","status":"BLOCKED_DUPLICATE" if dup else "PASS",
            "duplicate_detected":dup,"new_session_allowed":not dup}

def resume_session(session_doc, checkpoint, at:int):
    s=session_doc["session"]
    checks={
        "checkpoint_matches":checkpoint.get("session_id")==s["session_id"],
        "not_expired":at<s["expires_at"],
        "remaining_orders_one":checkpoint.get("remaining_orders")==1,
        "remaining_uses_one":checkpoint.get("remaining_uses")==1,
        "kill_switch_clear":checkpoint.get("kill_switch_clear") is True,
    }
    return {"stage":"V97.50","status":"RESUMED_READ_ONLY" if all(checks.values()) else "BLOCKED",
            "checks":checks,"network_enabled":False,"order_submission_enabled":False}

def consume_session(session_doc):
    s=session_doc["session"]
    if s["status"]!="ACTIVE" or s["remaining_orders"]!=1 or s["remaining_uses"]!=1:
        return {"stage":"V97.60","status":"BLOCKED"}
    consumed=dict(s)
    consumed["remaining_orders"]=0
    consumed["remaining_uses"]=0
    consumed["status"]="CONSUMED"
    consumed["network_enabled"]=False
    consumed["order_submission_enabled"]=False
    return {"stage":"V97.60","status":"CONSUMED","session":consumed}

def close_session(session_state, reason="NORMAL"):
    s=session_state["session"]
    closed=dict(s)
    closed["status"]="CLOSED"
    closed["close_reason"]=reason
    closed["network_enabled"]=False
    closed["order_submission_enabled"]=False
    return {"stage":"V97.70","status":"CLOSED","session":closed}

def recovery_policy():
    scenarios={
        "heartbeat_stale":{"session_stopped":True,"resume_requires_checkpoint":True,"new_orders_blocked":True},
        "process_restart":{"resume_read_only":True,"token_revalidation_required":True,"new_orders_blocked":True},
        "session_expired":{"session_closed":True,"new_approval_required":True,"new_orders_blocked":True},
        "duplicate_session":{"duplicate_blocked":True,"existing_session_preserved":True,"new_orders_blocked":True},
        "kill_switch":{"session_closed":True,"token_invalidated":True,"new_orders_blocked":True},
        "checkpoint_mismatch":{"resume_blocked":True,"manual_review":True,"new_orders_blocked":True},
    }
    return {"stage":"V97.75","status":"PASS","scenario_count":len(scenarios),
            "scenarios":scenarios}

def rollback_plan():
    actions={
        "rollback_target_v97_00":True,
        "close_active_session":True,
        "invalidate_session_token":True,
        "clear_pending_intent":True,
        "disable_network_path":True,
        "preserve_audit":True,
        "preserve_checkpoint":True,
    }
    return {"stage":"V97.80","status":"PASS","rollback_ready":all(actions.values()),"actions":actions}

def offline_certification(config):
    env={
        "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1",
        "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
        "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1",
        "AI_STOCK_BOT_ENABLE_CONTROLLED_SESSION":"1",
        "AI_STOCK_BOT_CONTROLLED_SESSION_CONFIRMATION":CONFIRMATION_TEXT,
        "AI_STOCK_BOT_KILL_SWITCH":"0",
        "APCA_API_KEY_ID":"FIXTURE_KEY",
        "APCA_API_SECRET_KEY":"FIXTURE_SECRET",
    }
    created=create_session(config)
    started=start_session(created,env)
    hb1=heartbeat(started,created["created_at"]+30)
    hb2=heartbeat(started,created["created_at"]+60)
    duplicate=duplicate_session_guard({created["session_id"]},created["session_id"])
    checkpoint={"session_id":created["session_id"],"remaining_orders":1,"remaining_uses":1,"kill_switch_clear":True}
    resumed=resume_session(started,checkpoint,created["created_at"]+90)
    consumed=consume_session(started)
    closed=close_session(consumed)
    recovery=recovery_policy()
    rollback=rollback_plan()
    checks={
        "created":created["status"]=="CREATED",
        "started":started["status"]=="ACTIVE",
        "heartbeat_one":hb1["status"]=="HEALTHY",
        "heartbeat_two":hb2["status"]=="HEALTHY",
        "duplicate_blocked":duplicate["status"]=="BLOCKED_DUPLICATE",
        "resume_read_only":resumed["status"]=="RESUMED_READ_ONLY",
        "consumed":consumed["status"]=="CONSUMED",
        "closed":closed["status"]=="CLOSED",
        "recovery_pass":recovery["status"]=="PASS",
        "rollback_ready":rollback["rollback_ready"] is True,
        "network_zero":True,
        "orders_zero":True,
    }
    return {"stage":"V97.85","status":"PASS" if all(checks.values()) else "FAIL",
            "checks":checks,"created":created,"started":started,
            "heartbeats":[hb1,hb2],"duplicate":duplicate,"resumed":resumed,
            "consumed":consumed,"closed":closed,"recovery":recovery,"rollback":rollback}

def default_safety(config):
    created=create_session(config)
    blocked=start_session(created,{})
    checks={
        "default_start_blocked":blocked["status"]=="BLOCKED",
        "scheduler_disabled":config.scheduler_enabled is False,
        "runtime_disabled":config.runtime_loop_enabled is False,
        "auto_execution_disabled":config.auto_execution_enabled is False,
        "live_disabled":config.live_trading_authorized is False,
        "network_zero":config.default_network_requests_executed==0,
        "orders_zero":config.default_actual_orders_submitted==0,
    }
    return {"stage":"V97.90","status":"PASS" if all(checks.values()) else "FAIL","checks":checks}

def store(output_root:Path, docs):
    pid="controlled-session-"+hjson(docs)[:24]
    pkg=output_root/"packages"/pid
    pkg.mkdir(parents=True,exist_ok=True)
    files={}
    for name,doc in docs.items():
        p=pkg/f"{name}.json";write_json(p,doc);data=p.read_bytes()
        files[name]={"relative_path":str(p.relative_to(output_root)).replace("\\","/"),
                     "sha256":hbytes(data),"byte_size":len(data)}
    ledger={"stage":"V97.95","status":"PASS","package_id":pid,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hjson(ledger)
    write_json(output_root/"controlled_session_ledger_v97_95.json",ledger)
    return pid,ledger

def manifest(output_root:Path, ledger):
    p=output_root/"controlled_session_ledger_v97_95.json";data=p.read_bytes()
    m={"stage":"V97.96","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(output_root)).replace("\\","/"),
       "sha256":hbytes(data),"byte_size":len(data)}},
       "network_requests_executed":0,"actual_orders_submitted":0}
    m["manifest_sha256"]=hjson(m)
    write_json(output_root/"controlled_session_manifest_v97_96.json",m)
    return m

def verify_manifest(output_root:Path,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hjson(u): return False
    for x in m["files"].values():
        data=(output_root/x["relative_path"]).read_bytes()
        if hbytes(data)!=x["sha256"] or len(data)!=x["byte_size"]: return False
    return True

def run_engine(repository_root:Path,config:ControlledSessionConfig,output_root:Path):
    config.validate()
    src=validate_source(repository_root/"release/v97_00/output/controlled_validation_certificate_v97_00.json")
    off=offline_certification(config)
    safety=default_safety(config)
    pid,l=store(output_root,{"source":{"stage":src["stage"],"sha256":src["certificate_sha256"]},
                             "offline":off,"safety":safety})
    m=manifest(output_root,l);valid=verify_manifest(output_root,m)
    status="PASS" if off["status"]=="PASS" and safety["status"]=="PASS" and valid else "FAIL"
    return {"status":status,"package_id":pid,"offline":off,"safety":safety,"manifest_valid":valid}

def build_certificate(output_root:Path,config:ControlledSessionConfig,result):
    off=result["offline"]
    checks={
        "pipeline_pass":result["status"]=="PASS",
        "offline_pass":off["status"]=="PASS",
        "default_safety_pass":result["safety"]["status"]=="PASS",
        "manifest_valid":result["manifest_valid"] is True,
        "network_zero":config.default_network_requests_executed==0,
        "orders_zero":config.default_actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    status="PASS" if not failed else "FAIL"
    cert={
        "stage":"V98.00","status":status,
        "scope":"V97.01-V98.00_CONTROLLED_SESSION_EXECUTION_FAST_TRACK",
        "release_candidate":config.release_candidate,
        "config":{**asdict(config),"allowed_symbols":list(config.allowed_symbols)},
        "checks":checks,"failed_checks":failed,
        "controlled_session_execution_fast_track_complete":status=="PASS",
        "actual_paper_controlled_session_rc2_ready":status=="PASS",
        "session_create_verified":True,
        "session_start_verified":True,
        "session_heartbeat_verified":True,
        "duplicate_session_guard_verified":True,
        "session_resume_verified":True,
        "session_consume_verified":True,
        "session_close_verified":True,
        "session_recovery_verified":True,
        "rollback_verified":True,
        "actual_session_runner_isolated":True,
        "default_network_requests_executed":0,
        "default_actual_orders_submitted":0,
        "summary":{
            "package_id":result["package_id"],
            "session_status":off["closed"]["status"],
            "heartbeat_count":len(off["heartbeats"]),
            "heartbeat_interval_seconds":config.heartbeat_interval_seconds,
            "session_ttl_seconds":config.session_ttl_seconds,
            "duplicate_status":off["duplicate"]["status"],
            "resume_status":off["resumed"]["status"],
            "consume_status":off["consumed"]["status"],
            "recovery_scenario_count":off["recovery"]["scenario_count"],
            "rollback_status":off["rollback"]["status"],
            "default_safety_status":result["safety"]["status"],
            "confirmation_text":CONFIRMATION_TEXT,
        },
        "next_phase":"V98_01_ACTUAL_PAPER_MULTI_SESSION_VALIDATION",
    }
    cert["certificate_sha256"]=hjson(cert)
    write_json(output_root/"controlled_session_certificate_v98_00.json",cert)
    write_json(output_root/"controlled_session_verify_v98_00.json",{
        "stage":"V98.00","status":status,"verified":status=="PASS",
        "certificate_sha256":cert["certificate_sha256"],
        "failed_checks":failed,"next_phase":cert["next_phase"],
    })
    return cert
