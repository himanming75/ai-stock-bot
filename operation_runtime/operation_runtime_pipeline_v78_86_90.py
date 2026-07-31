from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def safety() -> dict:
    return {
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
        "live_deployment_approved":False,
        "real_credentials_allowed":False,
    }

@dataclass(frozen=True)
class RuntimeSnapshot:
    runtime_id: str
    state: str
    heartbeat_sequence: int
    last_checkpoint_sequence: int
    restart_count: int
    failure_count: int
    snapshot_sha256: str

class OfflineOperationRuntime:
    VALID_TRANSITIONS={
        "CREATED":{"STARTING"},
        "STARTING":{"RUNNING","FAILED"},
        "RUNNING":{"PAUSED","FAILED","STOPPING"},
        "PAUSED":{"RUNNING","FAILED","STOPPING"},
        "FAILED":{"RECOVERING","STOPPING"},
        "RECOVERING":{"PAUSED","FAILED"},
        "STOPPING":{"STOPPED"},
        "STOPPED":set(),
    }

    def __init__(self, runtime_id:str, max_restarts:int):
        if not runtime_id:
            raise ValueError("runtime_id required")
        if max_restarts < 0:
            raise ValueError("max_restarts must be non-negative")
        self.runtime_id=runtime_id
        self.max_restarts=max_restarts
        self.state="CREATED"
        self.heartbeat_sequence=0
        self.last_checkpoint_sequence=0
        self.restart_count=0
        self.failure_count=0
        self.events=[]
        self.checkpoints=[]

    def _record(self,event_type:str,details:dict|None=None)->dict:
        base={
            "sequence":len(self.events)+1,
            "event_type":event_type,
            "state":self.state,
            "details":details or {},
            "previous_event_sha256":self.events[-1]["event_sha256"] if self.events else "",
        }
        event={**base,"event_sha256":digest_json(base)}
        self.events.append(event)
        return event

    def transition(self,target:str)->None:
        if target not in self.VALID_TRANSITIONS.get(self.state,set()):
            raise ValueError(f"invalid transition:{self.state}->{target}")
        self.state=target
        self._record("STATE_TRANSITION",{"target":target})

    def start(self)->None:
        self.transition("STARTING")
        self.transition("RUNNING")

    def heartbeat(self)->dict:
        if self.state not in ("RUNNING","PAUSED"):
            raise ValueError("heartbeat not allowed")
        self.heartbeat_sequence += 1
        return self._record("HEARTBEAT",{"heartbeat_sequence":self.heartbeat_sequence})

    def checkpoint(self)->dict:
        if self.state not in ("RUNNING","PAUSED"):
            raise ValueError("checkpoint not allowed")
        self.last_checkpoint_sequence += 1
        payload={
            "runtime_id":self.runtime_id,
            "checkpoint_sequence":self.last_checkpoint_sequence,
            "state":self.state,
            "heartbeat_sequence":self.heartbeat_sequence,
            "restart_count":self.restart_count,
            "failure_count":self.failure_count,
        }
        payload["checkpoint_sha256"]=digest_json(payload)
        self.checkpoints.append(payload)
        self._record("CHECKPOINT",{"checkpoint_sequence":self.last_checkpoint_sequence})
        return payload

    def fail(self,reason:str)->None:
        if self.state not in ("STARTING","RUNNING","PAUSED","RECOVERING"):
            raise ValueError("failure not allowed")
        self.failure_count += 1
        self.state="FAILED"
        self._record("FAILURE",{"reason":reason,"failure_count":self.failure_count})

    def recover(self)->None:
        if self.state!="FAILED":
            raise ValueError("runtime must be failed")
        if self.restart_count>=self.max_restarts:
            raise ValueError("restart limit exceeded")
        self.transition("RECOVERING")
        if not self.checkpoints:
            self.state="FAILED"
            self._record("RECOVERY_FAILED",{"reason":"checkpoint_missing"})
            raise ValueError("checkpoint required")
        latest=self.checkpoints[-1]
        expected=digest_json({k:v for k,v in latest.items() if k!="checkpoint_sha256"})
        if latest.get("checkpoint_sha256")!=expected:
            self.state="FAILED"
            self._record("RECOVERY_FAILED",{"reason":"checkpoint_hash"})
            raise ValueError("checkpoint hash mismatch")
        self.restart_count += 1
        self.state="PAUSED"
        self._record("RECOVERY_COMPLETED",{
            "checkpoint_sequence":latest["checkpoint_sequence"],
            "restart_count":self.restart_count
        })

    def stop(self)->None:
        if self.state not in ("RUNNING","PAUSED","FAILED"):
            raise ValueError("stop not allowed")
        self.transition("STOPPING")
        self.transition("STOPPED")

    def snapshot(self)->RuntimeSnapshot:
        base={
            "runtime_id":self.runtime_id,
            "state":self.state,
            "heartbeat_sequence":self.heartbeat_sequence,
            "last_checkpoint_sequence":self.last_checkpoint_sequence,
            "restart_count":self.restart_count,
            "failure_count":self.failure_count,
        }
        return RuntimeSnapshot(**base,snapshot_sha256=digest_json(base))

def verify_event_chain(events:list[dict])->bool:
    previous=""
    for idx,event in enumerate(events,1):
        if event.get("sequence")!=idx:
            raise ValueError("event sequence gap")
        if event.get("previous_event_sha256")!=previous:
            raise ValueError("event chain mismatch")
        expected=digest_json({k:v for k,v in event.items() if k!="event_sha256"})
        if event.get("event_sha256")!=expected:
            raise ValueError("event hash mismatch")
        previous=event["event_sha256"]
    return True

def build_operation_runtime_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.85" or cert.get("status")!="PASS":
        errors.append("deployment_certificate")
    if cert.get("certification_scope")!="OFFLINE_OPERATION_RUNTIME_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    runtime=config.get("operation_runtime",{})
    for key in ("runtime_id","max_restarts","heartbeat_count","allow_live_runtime"):
        if key not in runtime:
            errors.append(f"config_{key}")
    if runtime.get("allow_live_runtime") is not False:
        errors.append("live_runtime_flag")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.86.operation_runtime_foundation.1",
        "stage":"V78.86","status":status,
        "scope":"OFFLINE_OPERATION_RUNTIME_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "release_id":cert.get("release_id"),
        "operation_runtime":runtime,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_87_RUNTIME_HEALTH_HEARTBEAT",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"operation_runtime_foundation_v78_86.json",doc)
    ver={"stage":"V78.86","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"operation_runtime_foundation_verification_v78_86.json",ver)
    return doc

def run_runtime_health_heartbeat(foundation_path:Path,output_dir:Path)->dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.86" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    cfg=foundation.get("operation_runtime",{})
    runtime=None
    snapshot={}
    checkpoint={}
    try:
        runtime=OfflineOperationRuntime(str(cfg.get("runtime_id","")),int(cfg.get("max_restarts",0)))
        runtime.start()
        for _ in range(int(cfg.get("heartbeat_count",0))):
            runtime.heartbeat()
        checkpoint=runtime.checkpoint()
        snapshot=asdict(runtime.snapshot())
    except Exception as exc:
        errors.append(f"health_exception:{type(exc).__name__}")

    events=[] if runtime is None else runtime.events
    checks={
        "runtime_running":snapshot.get("state")=="RUNNING",
        "heartbeat_count_matches":snapshot.get("heartbeat_sequence")==int(cfg.get("heartbeat_count",0)),
        "checkpoint_created":snapshot.get("last_checkpoint_sequence")==1,
        "checkpoint_hash_valid":not checkpoint or checkpoint.get("checkpoint_sha256")==digest_json(
            {k:v for k,v in checkpoint.items() if k!="checkpoint_sha256"}
        ),
        "event_chain_valid":verify_event_chain(events) if events else False,
        "failure_count_zero":snapshot.get("failure_count")==0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("runtime_health_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.87.runtime_health_heartbeat.1",
        "stage":"V78.87","status":status,
        "runtime_snapshot":snapshot,
        "checkpoint":checkpoint,
        "runtime_events":events,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_88_RUNTIME_RECOVERY_RESTART",
    }
    doc["health_sha256"]=digest_json({k:v for k,v in doc.items() if k!="health_sha256"})
    write_json(output_dir/"runtime_health_heartbeat_v78_87.json",doc)
    ver={"stage":"V78.87","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "health_sha256":doc["health_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"runtime_health_heartbeat_verification_v78_87.json",ver)
    return doc

def run_runtime_recovery_restart(foundation_path:Path,health_path:Path,output_dir:Path)->dict:
    foundation,health=map(load_json,(foundation_path,health_path))
    errors=[]
    if foundation.get("stage")!="V78.86" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if health.get("stage")!="V78.87" or health.get("status")!="PASS":
        errors.append("health_input")
    cfg=foundation.get("operation_runtime",{})
    runtime=None
    snapshot={}
    try:
        runtime=OfflineOperationRuntime(str(cfg.get("runtime_id","")),int(cfg.get("max_restarts",0)))
        runtime.start()
        for _ in range(int(cfg.get("heartbeat_count",0))):
            runtime.heartbeat()
        runtime.checkpoint()
        runtime.fail("simulated_offline_failure")
        runtime.recover()
        runtime.heartbeat()
        snapshot=asdict(runtime.snapshot())
    except Exception as exc:
        errors.append(f"recovery_exception:{type(exc).__name__}")

    events=[] if runtime is None else runtime.events
    checks={
        "runtime_recovered_to_paused_or_running":snapshot.get("state") in ("PAUSED","RUNNING"),
        "restart_count_one":snapshot.get("restart_count")==1,
        "failure_count_one":snapshot.get("failure_count")==1,
        "checkpoint_retained":snapshot.get("last_checkpoint_sequence")==1,
        "event_chain_valid":verify_event_chain(events) if events else False,
        "recovery_event_present":any(x.get("event_type")=="RECOVERY_COMPLETED" for x in events),
        "post_recovery_heartbeat_present":any(
            x.get("event_type")=="HEARTBEAT" and x.get("details",{}).get("heartbeat_sequence")==int(cfg.get("heartbeat_count",0))+1
            for x in events
        ),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("runtime_recovery_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.88.runtime_recovery_restart.1",
        "stage":"V78.88","status":status,
        "runtime_snapshot":snapshot,
        "runtime_events":events,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_89_OPERATION_RUNTIME_SAFETY_GATE",
    }
    doc["recovery_sha256"]=digest_json({k:v for k,v in doc.items() if k!="recovery_sha256"})
    write_json(output_dir/"runtime_recovery_restart_v78_88.json",doc)
    ver={"stage":"V78.88","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "recovery_sha256":doc["recovery_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"runtime_recovery_restart_verification_v78_88.json",ver)
    return doc

def run_operation_runtime_safety_gate(foundation_path:Path,health_path:Path,
                                      recovery_path:Path,output_dir:Path)->dict:
    foundation,health,recovery=map(load_json,(foundation_path,health_path,recovery_path))
    errors=[]
    for expected,doc in (("V78.86",foundation),("V78.87",health),("V78.88",recovery)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    checks={
        "offline_runtime_scope":foundation.get("scope")=="OFFLINE_OPERATION_RUNTIME_ONLY",
        "health_checks_passed":health.get("failed_checks")==[],
        "recovery_checks_passed":recovery.get("failed_checks")==[],
        "live_runtime_disabled":foundation.get("operation_runtime",{}).get("allow_live_runtime") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,health,recovery)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,health,recovery)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,health,recovery)),
        "live_trading_not_authorized":all(x.get("live_trading_authorized") is False for x in (foundation,health,recovery)),
        "live_deployment_not_approved":all(x.get("live_deployment_approved") is False for x in (foundation,health,recovery)),
        "real_credentials_disabled":all(x.get("real_credentials_allowed") is False for x in (foundation,health,recovery)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("operation_runtime_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.89.operation_runtime_safety_gate.1",
        "stage":"V78.89","status":status,
        "gate_scope":"OFFLINE_FINAL_SYSTEM_CERTIFICATION_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_FINAL_SYSTEM_CERTIFICATION" if not errors else "BLOCK_FINAL_SYSTEM_CERTIFICATION",
        "live_runtime_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_90_OPERATION_RUNTIME_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"operation_runtime_safety_gate_v78_89.json",doc)
    ver={"stage":"V78.89","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"operation_runtime_safety_gate_verification_v78_89.json",ver)
    return doc

def issue_operation_runtime_certificate(v86:Path,v87:Path,v88:Path,v89:Path,
                                        foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v86,v87,v88,v89)))
    foundation=load_json(foundation_path)
    expected=["V78.86","V78.87","V78.88","V78.89"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.90.operation_runtime_certificate.1",
        "stage":"V78.90",
        "certificate_id":"OPERATION-RUNTIME-V78.90",
        "status":status,
        "decision":"certified_for_offline_final_system_certification" if not errors else "operation_runtime_rejected",
        "certification_scope":"OFFLINE_FINAL_SYSTEM_CERTIFICATION_DEVELOPMENT_ONLY",
        "runtime_id":foundation.get("operation_runtime",{}).get("runtime_id"),
        "release_id":foundation.get("release_id"),
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "live_deployment_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_91_FINAL_SYSTEM_CERTIFICATION_FOUNDATION" if not errors else "REPAIR_V78_90",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"operation_runtime_certificate_v78_90.json",cert)
    ver={"stage":"V78.90","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "runtime_id":cert["runtime_id"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"operation_runtime_certificate_verification_v78_90.json",ver)
    return cert
