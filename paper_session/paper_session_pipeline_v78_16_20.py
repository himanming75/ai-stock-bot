from __future__ import annotations
from dataclasses import dataclass, asdict
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

ALLOWED_TRANSITIONS = {
    "CREATED":{"STARTING"},
    "STARTING":{"RUNNING","FAILED"},
    "RUNNING":{"PAUSING","STOPPING","FAILED"},
    "PAUSING":{"PAUSED","FAILED"},
    "PAUSED":{"RESUMING","STOPPING","FAILED"},
    "RESUMING":{"RUNNING","FAILED"},
    "STOPPING":{"STOPPED","FAILED"},
    "FAILED":{"RECOVERING"},
    "RECOVERING":{"PAUSED","RUNNING","FAILED"},
    "STOPPED":set(),
}

@dataclass(frozen=True)
class SessionEvent:
    sequence: int
    event_type: str
    from_state: str
    to_state: str
    reason: str
    event_sha256: str

class PaperSessionManager:
    def __init__(self, session_id: str, starting_cash: float = 100000.0):
        if not session_id:
            raise ValueError("session_id required")
        self.session_id = session_id
        self.state = "CREATED"
        self.sequence = 0
        self.events: list[SessionEvent] = []
        self.starting_cash = float(starting_cash)
        self.cash = float(starting_cash)
        self.positions: dict[str,dict] = {}
        self.open_orders: dict[str,dict] = {}
        self.network_allowed = False
        self.broker_connected = False
        self.actual_orders_submitted = 0

    def transition(self, to_state: str, reason: str) -> SessionEvent:
        allowed = ALLOWED_TRANSITIONS.get(self.state,set())
        if to_state not in allowed:
            raise ValueError(f"invalid transition {self.state}->{to_state}")
        previous = self.state
        self.sequence += 1
        base = {
            "session_id":self.session_id,
            "sequence":self.sequence,
            "event_type":"SESSION_STATE_CHANGED",
            "from_state":previous,
            "to_state":to_state,
            "reason":reason,
        }
        evt = SessionEvent(
            sequence=self.sequence,
            event_type="SESSION_STATE_CHANGED",
            from_state=previous,
            to_state=to_state,
            reason=reason,
            event_sha256=digest_json(base),
        )
        self.events.append(evt)
        self.state = to_state
        return evt

    def start(self) -> list[SessionEvent]:
        return [self.transition("STARTING","start_requested"),
                self.transition("RUNNING","start_completed")]

    def pause(self) -> list[SessionEvent]:
        return [self.transition("PAUSING","pause_requested"),
                self.transition("PAUSED","pause_completed")]

    def resume(self) -> list[SessionEvent]:
        return [self.transition("RESUMING","resume_requested"),
                self.transition("RUNNING","resume_completed")]

    def stop(self) -> list[SessionEvent]:
        return [self.transition("STOPPING","stop_requested"),
                self.transition("STOPPED","stop_completed")]

    def fail(self, reason: str = "simulated_failure") -> SessionEvent:
        return self.transition("FAILED",reason)

    def checkpoint(self) -> dict:
        body = {
            "session_id":self.session_id,
            "state":self.state,
            "sequence":self.sequence,
            "starting_cash":self.starting_cash,
            "cash":self.cash,
            "positions":self.positions,
            "open_orders":self.open_orders,
            "events":[asdict(x) for x in self.events],
            "network_allowed":False,
            "broker_connected":False,
            "actual_orders_submitted":0,
        }
        return {**body,"checkpoint_sha256":digest_json(body)}

    @classmethod
    def restore(cls, checkpoint: dict) -> "PaperSessionManager":
        expected = digest_json({k:v for k,v in checkpoint.items() if k!="checkpoint_sha256"})
        if checkpoint.get("checkpoint_sha256") != expected:
            raise ValueError("checkpoint hash mismatch")
        obj = cls(checkpoint["session_id"],checkpoint["starting_cash"])
        obj.state = checkpoint["state"]
        obj.sequence = int(checkpoint["sequence"])
        obj.cash = float(checkpoint["cash"])
        obj.positions = dict(checkpoint["positions"])
        obj.open_orders = dict(checkpoint["open_orders"])
        obj.events = [SessionEvent(**x) for x in checkpoint["events"]]
        if checkpoint.get("network_allowed") is not False:
            raise ValueError("network must remain disabled")
        if checkpoint.get("broker_connected") is not False:
            raise ValueError("broker must remain disconnected")
        if checkpoint.get("actual_orders_submitted") != 0:
            raise ValueError("actual orders must remain zero")
        return obj

    def recover(self, target_state: str = "PAUSED") -> list[SessionEvent]:
        if self.state != "FAILED":
            raise ValueError("session is not failed")
        if target_state not in ("PAUSED","RUNNING"):
            raise ValueError("invalid recovery target")
        return [self.transition("RECOVERING","recovery_started"),
                self.transition(target_state,"recovery_completed")]

def build_session_manager_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json,(certificate_path,config_path))
    errors = []
    if cert.get("stage")!="V78.15" or cert.get("status")!="PASS":
        errors.append("event_bus_certificate")
    if cert.get("certification_scope")!="OFFLINE_SESSION_MANAGER_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    session = config.get("paper_session",{})
    for key in ("session_id","starting_cash","default_state","checkpoint_enabled"):
        if key not in session:
            errors.append(f"config_{key}")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.16.paper_session_manager_foundation.1",
        "stage":"V78.16","status":status,
        "scope":"OFFLINE_PAPER_SESSION_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "paper_session":session,
        "allowed_transitions":{k:sorted(v) for k,v in ALLOWED_TRANSITIONS.items()},
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_17_SESSION_LIFECYCLE_STATE_MACHINE",
    }
    doc["foundation_sha256"] = digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"paper_session_manager_foundation_v78_16.json",doc)
    ver={"stage":"V78.16","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_session_manager_foundation_verification_v78_16.json",ver)
    return doc

def run_session_lifecycle(foundation_path: Path, output_dir: Path) -> dict:
    foundation = load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.16" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    cfg=foundation.get("paper_session",{})
    manager=PaperSessionManager(cfg.get("session_id","PAPER-SESSION"),cfg.get("starting_cash",100000.0))
    try:
        manager.start();manager.pause();manager.resume();manager.stop()
    except Exception as exc:
        errors.append(f"lifecycle_exception:{type(exc).__name__}")
    states=[x.to_state for x in manager.events]
    checks={
        "final_state_stopped":manager.state=="STOPPED",
        "expected_sequence":manager.sequence==8,
        "expected_states":states==["STARTING","RUNNING","PAUSING","PAUSED","RESUMING","RUNNING","STOPPING","STOPPED"],
        "event_hashes_unique":len({x.event_sha256 for x in manager.events})==len(manager.events),
        "network_disabled":manager.network_allowed is False,
        "actual_orders_zero":manager.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("lifecycle_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.17.session_lifecycle.1","stage":"V78.17","status":status,
        "session_id":manager.session_id,"final_state":manager.state,
        "events":[asdict(x) for x in manager.events],
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_18_SESSION_CHECKPOINT_RESUME",
    }
    doc["lifecycle_sha256"]=digest_json({k:v for k,v in doc.items() if k!="lifecycle_sha256"})
    write_json(output_dir/"session_lifecycle_state_machine_v78_17.json",doc)
    ver={"stage":"V78.17","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"lifecycle_sha256":doc["lifecycle_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"session_lifecycle_state_machine_verification_v78_17.json",ver)
    return doc

def run_checkpoint_resume(foundation_path: Path, output_dir: Path) -> dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.16" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    cfg=foundation.get("paper_session",{})
    manager=PaperSessionManager(cfg.get("session_id","PAPER-SESSION"),cfg.get("starting_cash",100000.0))
    try:
        manager.start()
        manager.cash=99500.0
        manager.positions={"AAPL":{"symbol":"AAPL","quantity":5,"average_price":100.0}}
        manager.open_orders={"ORD-2":{"symbol":"MSFT","side":"buy","quantity":1}}
        manager.fail("simulated_crash")
        cp=manager.checkpoint()
        restored=PaperSessionManager.restore(cp)
        restored.recover("PAUSED")
        resumed_cp=restored.checkpoint()
    except Exception as exc:
        cp={};resumed_cp={};restored=None
        errors.append(f"checkpoint_exception:{type(exc).__name__}")
    checks={
        "checkpoint_hash_valid":bool(cp) and cp.get("checkpoint_sha256")==digest_json({k:v for k,v in cp.items() if k!="checkpoint_sha256"}),
        "restored_state_paused":restored is not None and restored.state=="PAUSED",
        "cash_restored":restored is not None and restored.cash==99500.0,
        "positions_restored":restored is not None and restored.positions=={"AAPL":{"symbol":"AAPL","quantity":5,"average_price":100.0}},
        "open_orders_restored":restored is not None and "ORD-2" in restored.open_orders,
        "sequence_continued":restored is not None and restored.sequence==5,
        "resume_checkpoint_valid":bool(resumed_cp) and resumed_cp.get("checkpoint_sha256")==digest_json({k:v for k,v in resumed_cp.items() if k!="checkpoint_sha256"}),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("checkpoint_resume_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.18.session_checkpoint_resume.1","stage":"V78.18","status":status,
        "checkpoint":cp,"resumed_checkpoint":resumed_cp,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_19_SESSION_MANAGER_SAFETY_GATE",
    }
    doc["checkpoint_resume_sha256"]=digest_json({k:v for k,v in doc.items() if k!="checkpoint_resume_sha256"})
    write_json(output_dir/"session_checkpoint_resume_v78_18.json",doc)
    ver={"stage":"V78.18","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"checkpoint_resume_sha256":doc["checkpoint_resume_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"session_checkpoint_resume_verification_v78_18.json",ver)
    return doc

def run_session_manager_safety_gate(foundation_path: Path,lifecycle_path: Path,checkpoint_path: Path,output_dir: Path)->dict:
    foundation,lifecycle,checkpoint=map(load_json,(foundation_path,lifecycle_path,checkpoint_path))
    errors=[]
    for expected,doc in (("V78.16",foundation),("V78.17",lifecycle),("V78.18",checkpoint)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    checks={
        "default_state_created":foundation.get("paper_session",{}).get("default_state")=="CREATED",
        "checkpoint_enabled":foundation.get("paper_session",{}).get("checkpoint_enabled") is True,
        "lifecycle_passed":lifecycle.get("failed_checks")==[],
        "checkpoint_resume_passed":checkpoint.get("failed_checks")==[],
        "invalid_transitions_blocked":"STOPPED" in foundation.get("allowed_transitions",{}) and foundation["allowed_transitions"]["STOPPED"]==[],
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,lifecycle,checkpoint)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,lifecycle,checkpoint)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,lifecycle,checkpoint)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("session_manager_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.19.session_manager_safety_gate.1","stage":"V78.19","status":status,
        "gate_scope":"OFFLINE_RUNTIME_SCHEDULER_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_RUNTIME_SCHEDULER" if not errors else "BLOCK_RUNTIME_SCHEDULER",
        "real_broker_connection_approved":False,"actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_20_SESSION_MANAGER_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"session_manager_safety_gate_v78_19.json",doc)
    ver={"stage":"V78.19","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"safety_gate_sha256":doc["safety_gate_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"session_manager_safety_gate_verification_v78_19.json",ver)
    return doc

def issue_session_manager_certificate(v16:Path,v17:Path,v18:Path,v19:Path,foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v16,v17,v18,v19)))
    foundation=load_json(foundation_path)
    expected=["V78.16","V78.17","V78.18","V78.19"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.20.session_manager_certificate.1","stage":"V78.20",
        "certificate_id":"PAPER-SESSION-MANAGER-V78.20","status":status,
        "decision":"certified_for_offline_runtime_scheduler" if not errors else "session_manager_rejected",
        "certification_scope":"OFFLINE_RUNTIME_SCHEDULER_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,"real_credentials_approved":False,
        "network_transport_approved":False,"actual_order_submission_approved":False,
        "live_trading_approved":False,"certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,**safety(),
        "next_phase":"V78_21_RUNTIME_SCHEDULER_FOUNDATION" if not errors else "REPAIR_V78_20",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"session_manager_certificate_v78_20.json",cert)
    ver={"stage":"V78.20","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"session_manager_certificate_verification_v78_20.json",ver)
    return cert
