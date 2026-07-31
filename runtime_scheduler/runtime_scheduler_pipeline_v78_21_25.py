from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable
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
class ScheduledJob:
    job_id: str
    interval_ticks: int
    start_tick: int
    max_retries: int
    enabled: bool = True

@dataclass(frozen=True)
class JobExecutionRecord:
    execution_id: str
    job_id: str
    tick: int
    attempt: int
    status: str
    result_sha256: str | None = None
    error: str | None = None

class JobRegistry:
    def __init__(self):
        self._jobs: dict[str,ScheduledJob] = {}
        self._handlers: dict[str,Callable[[int],Any]] = {}

    def register(self, job: ScheduledJob, handler: Callable[[int],Any]) -> None:
        if not job.job_id.strip():
            raise ValueError("job_id required")
        if job.job_id in self._jobs:
            raise ValueError("job already registered")
        if job.interval_ticks <= 0:
            raise ValueError("interval_ticks must be positive")
        if job.start_tick < 0:
            raise ValueError("start_tick must be non-negative")
        if job.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._jobs[job.job_id] = job
        self._handlers[job.job_id] = handler

    def jobs(self) -> list[ScheduledJob]:
        return [self._jobs[k] for k in sorted(self._jobs)]

    def due_jobs(self, tick: int) -> list[ScheduledJob]:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        result=[]
        for job in self.jobs():
            if not job.enabled or tick < job.start_tick:
                continue
            if (tick-job.start_tick) % job.interval_ticks == 0:
                result.append(job)
        return result

    def handler(self, job_id: str) -> Callable[[int],Any]:
        return self._handlers[job_id]

class DeterministicTickScheduler:
    def __init__(self, registry: JobRegistry):
        self.registry = registry
        self.current_tick = -1
        self.execution_records: list[JobExecutionRecord] = []
        self.completed_keys: set[tuple[str,int]] = set()
        self.failed_keys: set[tuple[str,int]] = set()
        self.network_allowed=False
        self.broker_connected=False
        self.actual_orders_submitted=0

    def run_tick(self, tick: int) -> list[JobExecutionRecord]:
        if tick != self.current_tick + 1:
            raise ValueError("ticks must be contiguous")
        self.current_tick = tick
        created=[]
        for job in self.registry.due_jobs(tick):
            key=(job.job_id,tick)
            if key in self.completed_keys:
                continue
            handler=self.registry.handler(job.job_id)
            success=False
            last_error=None
            for attempt in range(1,job.max_retries+2):
                execution_id=f"{job.job_id}:{tick}:{attempt}"
                try:
                    result=handler(tick)
                    rec=JobExecutionRecord(
                        execution_id=execution_id,job_id=job.job_id,tick=tick,attempt=attempt,
                        status="SUCCESS",result_sha256=digest_json(result)
                    )
                    self.execution_records.append(rec);created.append(rec)
                    self.completed_keys.add(key);success=True
                    break
                except Exception as exc:
                    last_error=f"{type(exc).__name__}:{exc}"
                    rec=JobExecutionRecord(
                        execution_id=execution_id,job_id=job.job_id,tick=tick,attempt=attempt,
                        status="RETRY" if attempt<=job.max_retries else "FAILED",error=last_error
                    )
                    self.execution_records.append(rec);created.append(rec)
            if not success:
                self.failed_keys.add(key)
        return created

    def run_until(self, final_tick: int) -> list[JobExecutionRecord]:
        if final_tick < self.current_tick:
            raise ValueError("cannot move backward")
        for tick in range(self.current_tick+1, final_tick+1):
            self.run_tick(tick)
        return list(self.execution_records)

    def checkpoint(self) -> dict:
        body={
            "current_tick":self.current_tick,
            "execution_records":[asdict(x) for x in self.execution_records],
            "completed_keys":[list(x) for x in sorted(self.completed_keys)],
            "failed_keys":[list(x) for x in sorted(self.failed_keys)],
            "network_allowed":False,
            "broker_connected":False,
            "actual_orders_submitted":0,
        }
        return {**body,"checkpoint_sha256":digest_json(body)}

    @classmethod
    def restore(cls, registry: JobRegistry, checkpoint: dict) -> "DeterministicTickScheduler":
        expected=digest_json({k:v for k,v in checkpoint.items() if k!="checkpoint_sha256"})
        if checkpoint.get("checkpoint_sha256")!=expected:
            raise ValueError("checkpoint hash mismatch")
        if checkpoint.get("network_allowed") is not False:
            raise ValueError("network must remain disabled")
        if checkpoint.get("broker_connected") is not False:
            raise ValueError("broker must remain disconnected")
        if checkpoint.get("actual_orders_submitted")!=0:
            raise ValueError("actual orders must remain zero")
        obj=cls(registry)
        obj.current_tick=int(checkpoint["current_tick"])
        obj.execution_records=[JobExecutionRecord(**x) for x in checkpoint["execution_records"]]
        obj.completed_keys={tuple(x) for x in checkpoint["completed_keys"]}
        obj.failed_keys={tuple(x) for x in checkpoint["failed_keys"]}
        return obj

    def health(self) -> dict:
        return {
            "status":"HEALTHY",
            "current_tick":self.current_tick,
            "execution_record_count":len(self.execution_records),
            "completed_job_tick_count":len(self.completed_keys),
            "failed_job_tick_count":len(self.failed_keys),
            "network_allowed":False,
            "broker_connected":False,
            "actual_orders_submitted":0,
        }

def build_runtime_scheduler_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.20" or cert.get("status")!="PASS":
        errors.append("session_manager_certificate")
    if cert.get("certification_scope")!="OFFLINE_RUNTIME_SCHEDULER_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    scheduler=config.get("runtime_scheduler",{})
    for key in ("mode","final_tick","jobs","checkpoint_enabled"):
        if key not in scheduler:
            errors.append(f"config_{key}")
    if scheduler.get("mode")!="deterministic_offline":
        errors.append("mode")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.21.runtime_scheduler_foundation.1",
        "stage":"V78.21","status":status,"scope":"OFFLINE_DETERMINISTIC_SCHEDULER_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "runtime_scheduler":scheduler,
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_22_SCHEDULED_JOB_REGISTRY",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"runtime_scheduler_foundation_v78_21.json",doc)
    ver={"stage":"V78.21","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"runtime_scheduler_foundation_verification_v78_21.json",ver)
    return doc

def build_scheduled_job_registry(foundation_path: Path, output_dir: Path) -> dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.21" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    registry=JobRegistry()
    seen=[]
    def noop_factory(job_id:str):
        return lambda tick:{"job_id":job_id,"tick":tick,"status":"ok"}
    try:
        for spec in foundation.get("runtime_scheduler",{}).get("jobs",[]):
            job=ScheduledJob(
                job_id=spec["job_id"],
                interval_ticks=int(spec["interval_ticks"]),
                start_tick=int(spec.get("start_tick",0)),
                max_retries=int(spec.get("max_retries",0)),
                enabled=bool(spec.get("enabled",True)),
            )
            registry.register(job,noop_factory(job.job_id))
            seen.append(asdict(job))
    except Exception as exc:
        errors.append(f"registry_exception:{type(exc).__name__}")
    due_map={str(tick):[x.job_id for x in registry.due_jobs(tick)] for tick in range(0,6)}
    checks={
        "job_count_expected":len(seen)==3,
        "job_ids_unique":len({x["job_id"] for x in seen})==len(seen),
        "tick_zero_jobs":due_map["0"]==["heartbeat","market_clock"],
        "tick_two_jobs":due_map["2"]==["heartbeat"],
        "tick_three_jobs":due_map["3"]==["market_clock"],
        "tick_five_jobs":due_map["5"]==["portfolio_snapshot"],
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("job_registry_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.22.scheduled_job_registry.1","stage":"V78.22","status":status,
        "jobs":seen,"due_map":due_map,"checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_23_DETERMINISTIC_TICK_JOB_EXECUTION",
    }
    doc["registry_sha256"]=digest_json({k:v for k,v in doc.items() if k!="registry_sha256"})
    write_json(output_dir/"scheduled_job_registry_v78_22.json",doc)
    ver={"stage":"V78.22","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"registry_sha256":doc["registry_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"scheduled_job_registry_verification_v78_22.json",ver)
    return doc

def run_deterministic_tick_job_execution(foundation_path: Path, output_dir: Path) -> dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.21" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    registry=JobRegistry()
    calls={"heartbeat":[],"market_clock":[],"portfolio_snapshot":[]}
    flaky={"count":0}
    registry.register(ScheduledJob("heartbeat",2,0,0),lambda tick:calls["heartbeat"].append(tick) or {"tick":tick})
    registry.register(ScheduledJob("market_clock",3,0,1),
        lambda tick: (_ for _ in ()).throw(RuntimeError("transient")) if tick==3 and flaky.update(count=flaky["count"]+1) is None and flaky["count"]==1
        else calls["market_clock"].append(tick) or {"tick":tick})
    registry.register(ScheduledJob("portfolio_snapshot",5,5,0),
        lambda tick:calls["portfolio_snapshot"].append(tick) or {"tick":tick})
    scheduler=DeterministicTickScheduler(registry)
    try:
        scheduler.run_until(5)
        cp=scheduler.checkpoint()
        restored=DeterministicTickScheduler.restore(registry,cp)
        restored.run_until(7)
        final_cp=restored.checkpoint()
    except Exception as exc:
        cp={};final_cp={};restored=None
        errors.append(f"execution_exception:{type(exc).__name__}")
    records=[asdict(x) for x in (restored.execution_records if restored else [])]
    checks={
        "heartbeat_ticks":calls["heartbeat"]==[0,2,4,6],
        "market_clock_ticks":calls["market_clock"]==[0,3,6],
        "portfolio_snapshot_ticks":calls["portfolio_snapshot"]==[5],
        "transient_retry_recorded":any(x["job_id"]=="market_clock" and x["tick"]==3 and x["status"]=="RETRY" for x in records),
        "retry_then_success":any(x["job_id"]=="market_clock" and x["tick"]==3 and x["status"]=="SUCCESS" for x in records),
        "execution_ids_unique":len({x["execution_id"] for x in records})==len(records),
        "checkpoint_valid":bool(cp) and cp.get("checkpoint_sha256")==digest_json({k:v for k,v in cp.items() if k!="checkpoint_sha256"}),
        "restored_tick_continued":restored is not None and restored.current_tick==7,
        "actual_orders_zero":restored is not None and restored.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("tick_execution_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.23.deterministic_tick_execution.1","stage":"V78.23","status":status,
        "execution_records":records,"checkpoint":cp,"final_checkpoint":final_cp,
        "calls":calls,"checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_24_RUNTIME_SCHEDULER_SAFETY_GATE",
    }
    doc["execution_sha256"]=digest_json({k:v for k,v in doc.items() if k!="execution_sha256"})
    write_json(output_dir/"deterministic_tick_job_execution_v78_23.json",doc)
    ver={"stage":"V78.23","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"execution_sha256":doc["execution_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"deterministic_tick_job_execution_verification_v78_23.json",ver)
    return doc

def run_runtime_scheduler_safety_gate(foundation_path:Path,registry_path:Path,execution_path:Path,output_dir:Path)->dict:
    foundation,registry,execution=map(load_json,(foundation_path,registry_path,execution_path))
    errors=[]
    for expected,doc in (("V78.21",foundation),("V78.22",registry),("V78.23",execution)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    records=execution.get("execution_records",[])
    checks={
        "deterministic_offline_mode":foundation.get("runtime_scheduler",{}).get("mode")=="deterministic_offline",
        "checkpoint_enabled":foundation.get("runtime_scheduler",{}).get("checkpoint_enabled") is True,
        "registry_checks_passed":registry.get("failed_checks")==[],
        "execution_checks_passed":execution.get("failed_checks")==[],
        "execution_ids_unique":len({x["execution_id"] for x in records})==len(records),
        "no_duplicate_success_per_job_tick":len({
            (x["job_id"],x["tick"]) for x in records if x["status"]=="SUCCESS"
        })==sum(x["status"]=="SUCCESS" for x in records),
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,registry,execution)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,registry,execution)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,registry,execution)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("runtime_scheduler_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.24.runtime_scheduler_safety_gate.1","stage":"V78.24","status":status,
        "gate_scope":"OFFLINE_MARKET_CLOCK_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_MARKET_CLOCK" if not errors else "BLOCK_MARKET_CLOCK",
        "real_broker_connection_approved":False,"actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_25_RUNTIME_SCHEDULER_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"runtime_scheduler_safety_gate_v78_24.json",doc)
    ver={"stage":"V78.24","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"safety_gate_sha256":doc["safety_gate_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"runtime_scheduler_safety_gate_verification_v78_24.json",ver)
    return doc

def issue_runtime_scheduler_certificate(v21:Path,v22:Path,v23:Path,v24:Path,foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v21,v22,v23,v24)));foundation=load_json(foundation_path)
    expected=["V78.21","V78.22","V78.23","V78.24"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.25.runtime_scheduler_certificate.1","stage":"V78.25",
        "certificate_id":"RUNTIME-SCHEDULER-V78.25","status":status,
        "decision":"certified_for_offline_market_clock" if not errors else "runtime_scheduler_rejected",
        "certification_scope":"OFFLINE_MARKET_CLOCK_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,"real_credentials_approved":False,
        "network_transport_approved":False,"actual_order_submission_approved":False,
        "live_trading_approved":False,"certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_26_MARKET_CLOCK_FOUNDATION" if not errors else "REPAIR_V78_25",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"runtime_scheduler_certificate_v78_25.json",cert)
    ver={"stage":"V78.25","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"runtime_scheduler_certificate_verification_v78_25.json",ver)
    return cert
