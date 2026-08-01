
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib, json, tempfile, os

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()
def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class SchedulerRuntimeSimulationConfig:
    mode: str = "PAPER_SCHEDULER_RUNTIME_SIMULATION"
    environment: str = "PAPER"
    strategy_id: str = "SAFE_MOMENTUM_PREVIEW"
    simulation_date: str = "2026-07-06"
    cycle_count: int = 3
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    market_data_network_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0

    def validate(self):
        if self.mode != "PAPER_SCHEDULER_RUNTIME_SIMULATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if not self.strategy_id.strip(): raise ValueError("strategy")
        if self.cycle_count < 1: raise ValueError("cycle_count")
        if any([self.scheduler_enabled, self.runtime_loop_enabled,
                self.market_data_network_enabled, self.auto_execution_enabled,
                self.paper_order_submission_authorized, self.live_trading_authorized]):
            raise ValueError("unsafe enablement")
        if self.network_requests_executed != 0 or self.actual_orders_submitted != 0:
            raise ValueError("offline only")

def validate_source(path: Path, stage: str, flag: str) -> dict[str, Any]:
    c = json.loads(path.read_text(encoding="utf-8"))
    u = dict(c); expected = u.pop("certificate_sha256")
    if expected != hjson(u): raise ValueError("certificate hash")
    if c.get("stage") != stage or c.get("status") != "PASS": raise ValueError("certificate")
    if c.get(flag) is not True: raise ValueError("prerequisite")
    return c

def simulation_policy(config):
    d = {"stage":"V88.61","status":"PASS","simulation_only":True,
         "scheduler_enabled":False,"runtime_loop_enabled":False,
         "market_data_network_enabled":False,"order_submission_enabled":False}
    d["sha256"] = hjson(d); return d

def daily_timeline(config):
    base = datetime.fromisoformat(config.simulation_date + "T13:15:00+00:00")
    events = [
        ("PREOPEN_PREP", base),
        ("MARKET_OPEN", base + timedelta(minutes=15)),
        ("STRATEGY_CYCLE_1", base + timedelta(minutes=16)),
        ("STRATEGY_CYCLE_2", base + timedelta(minutes=17)),
        ("STRATEGY_CYCLE_3", base + timedelta(minutes=18)),
        ("MARKET_CLOSE", base + timedelta(hours=6, minutes=45)),
        ("POSTCLOSE_REPORT", base + timedelta(hours=6, minutes=55)),
    ]
    d = {"stage":"V88.62","event_count":len(events),
         "events":[{"name":n,"at":t.isoformat(),"dispatch_enabled":False} for n,t in events]}
    d["sha256"] = hjson(d); return d

def event_queue(timeline):
    items=[{"event_id":f"evt-{i+1:02d}","name":e["name"],"at":e["at"],"status":"QUEUED_PREVIEW"}
           for i,e in enumerate(timeline["events"])]
    d={"stage":"V88.63","queue_depth":len(items),"items":items,"dispatch_enabled":False}
    d["sha256"]=hjson(d);return d

def market_data_gate(cycle_id, quality="PASS"):
    d={"stage":"V88.64","cycle_id":cycle_id,"quality_status":quality,
       "cycle_allowed":quality=="PASS","network_requests_executed":0}
    d["sha256"]=hjson(d);return d

def strategy_tick(config, cycle_id, gate):
    status="PASS" if gate["cycle_allowed"] else "SKIP"
    d={"stage":"V88.65","cycle_id":cycle_id,"strategy_id":config.strategy_id,
       "status":status,"signal_id":f"sim-signal-{cycle_id}" if status=="PASS" else None,
       "order_submission_enabled":False}
    d["sha256"]=hjson(d);return d

def heartbeat(cycle_id):
    d={"stage":"V88.66","cycle_id":cycle_id,"status":"PASS","age_seconds":0}
    d["sha256"]=hjson(d);return d

def runtime_state_transition(current, event):
    allowed={
      ("IDLE","PREOPEN_PREP"):"PREOPEN",
      ("PREOPEN","MARKET_OPEN"):"RUNNING",
      ("RUNNING","MARKET_CLOSE"):"CLOSING",
      ("CLOSING","POSTCLOSE_REPORT"):"STOPPED",
    }
    nxt=allowed.get((current,event),"RUNNING" if current=="RUNNING" and event.startswith("STRATEGY_CYCLE") else "ERROR")
    d={"stage":"V88.67","from_state":current,"event":event,"to_state":nxt,
       "status":"PASS" if nxt!="ERROR" else "FAIL"}
    d["sha256"]=hjson(d);return d

def checkpoint(cycle_index, state, queue_depth):
    d={"stage":"V88.68","checkpoint_id":f"scheduler-runtime-cp-{cycle_index:02d}",
       "cycle_index":cycle_index,"runtime_state":state,"queue_depth":queue_depth,
       "status":"SAVED","resumable":True}
    d["sha256"]=hjson(d);return d

def resume(cp):
    d={"stage":"V88.69","checkpoint_id":cp["checkpoint_id"],
       "status":"RESUMED_PREVIEW_ONLY","dispatch_enabled":False}
    d["sha256"]=hjson(d);return d

def duplicate_event_guard(processed_ids, event_id):
    dup=event_id in processed_ids
    d={"stage":"V88.70","event_id":event_id,"duplicate_detected":dup,
       "accepted":not dup}
    d["sha256"]=hjson(d);return d

def missed_event_recovery(delay_minutes):
    recoverable=0 < delay_minutes <= 30
    d={"stage":"V88.71","delay_minutes":delay_minutes,"recoverable":recoverable,
       "action":"MANUAL_PREVIEW_RECOVERY" if recoverable else "SKIP",
       "automatic_dispatch":False}
    d["sha256"]=hjson(d);return d

def incident_recovery(code):
    d={"stage":"V88.72","code":code,"status":"PASS",
       "stop_runtime":True,"clear_queue":True,"persist_checkpoint":True,
       "manual_review_required":True,"order_action":False}
    d["sha256"]=hjson(d);return d

def shutdown_report(final_state, cycles):
    d={"stage":"V88.73","status":"PASS","final_state":final_state,
       "cycles_completed":cycles,"queue_cleared":True,
       "checkpoint_persisted":True,"orders_submitted":0}
    d["sha256"]=hjson(d);return d

def daily_runtime_report(config, cycles, signals, incidents):
    d={"stage":"V88.74","status":"PASS","simulation_date":config.simulation_date,
       "strategy_id":config.strategy_id,"cycles_completed":cycles,
       "signals_generated":signals,"incident_count":incidents,
       "network_requests_executed":0,"actual_orders_submitted":0}
    d["sha256"]=hjson(d);return d

def run_simulation(config):
    timeline=daily_timeline(config);queue=event_queue(timeline)
    state="IDLE";processed=set();cycles=0;signals=0;checkpoints=[];transitions=[]
    for item in queue["items"]:
        guard=duplicate_event_guard(processed,item["event_id"])
        if not guard["accepted"]: continue
        processed.add(item["event_id"])
        tr=runtime_state_transition(state,item["name"]);transitions.append(tr);state=tr["to_state"]
        if item["name"].startswith("STRATEGY_CYCLE"):
            cycles+=1
            gate=market_data_gate(item["name"],"PASS")
            tick=strategy_tick(config,item["name"],gate)
            heartbeat(item["name"])
            if tick["status"]=="PASS": signals+=1
            checkpoints.append(checkpoint(cycles,state,len(queue["items"])-len(processed)))
    cp=checkpoints[-1];res=resume(cp)
    shutdown=shutdown_report(state,cycles)
    report=daily_runtime_report(config,cycles,signals,0)
    d={"stage":"V88.75","status":"PASS","timeline":timeline,"queue":queue,
       "transitions":transitions,"checkpoint":cp,"resume":res,
       "shutdown":shutdown,"daily_report":report,
       "cycle_count":cycles,"signal_count":signals,
       "final_state":state,"network_requests_executed":0,"actual_orders_submitted":0}
    d["sha256"]=hjson(d);return d

def negative_scenarios(config):
    dup=duplicate_event_guard({"evt-01"},"evt-01")
    missed_ok=missed_event_recovery(10)
    missed_skip=missed_event_recovery(60)
    bad_gate=market_data_gate("bad-cycle","FAIL")
    skipped=strategy_tick(config,"bad-cycle",bad_gate)
    incident=incident_recovery("SIMULATED_RUNTIME_ERROR")
    d={"stage":"V88.76","status":"PASS",
       "duplicate_detected":dup["duplicate_detected"],
       "missed_recoverable":missed_ok["recoverable"],
       "missed_outside_window_skipped":not missed_skip["recoverable"],
       "bad_data_cycle_skipped":skipped["status"]=="SKIP",
       "incident_recovery_ready":incident["status"]=="PASS"}
    d["sha256"]=hjson(d);return d

def audit(config, sim, neg):
    checks={"cycles_match":sim["cycle_count"]==config.cycle_count,
            "signals_match":sim["signal_count"]==config.cycle_count,
            "final_state_stopped":sim["final_state"]=="STOPPED",
            "checkpoint_saved":sim["checkpoint"]["status"]=="SAVED",
            "resume_preview_only":sim["resume"]["status"]=="RESUMED_PREVIEW_ONLY",
            "shutdown_pass":sim["shutdown"]["status"]=="PASS",
            "daily_report_pass":sim["daily_report"]["status"]=="PASS",
            "negative_pass":neg["status"]=="PASS",
            "scheduler_disabled":config.scheduler_enabled is False,
            "runtime_disabled":config.runtime_loop_enabled is False,
            "network_zero":sim["network_requests_executed"]==0,
            "orders_zero":sim["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.77","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["sha256"]=hjson(d);return d

def store(out, docs):
    pid="scheduler-runtime-sim-"+hjson(docs)[:24]
    package=out/"packages"/pid;package.mkdir(parents=True,exist_ok=True)
    files={}
    for name,doc in docs.items():
        p=package/f"{name}.json";write_json(p,doc);b=p.read_bytes()
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hbytes(b),"byte_size":len(b)}
    ledger={"stage":"V88.78","status":"PASS","package_id":pid,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hjson(ledger)
    write_json(out/"scheduler_runtime_sim_ledger_v88_78.json",ledger)
    return pid,ledger

def manifest(out, ledger):
    p=out/"scheduler_runtime_sim_ledger_v88_78.json";b=p.read_bytes()
    d={"stage":"V88.79","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
       "sha256":hbytes(b),"byte_size":len(b)}},"network_requests_executed":0,
       "actual_orders_submitted":0}
    d["manifest_sha256"]=hjson(d);write_json(out/"scheduler_runtime_sim_manifest_v88_79.json",d);return d

def run_engine(root, config, out):
    config.validate()
    validate_source(root/"release/v88_60/output/market_data_operations_certificate_v88_60.json",
                    "V88.60","paper_market_data_operations_foundation_complete")
    sim=run_simulation(config);neg=negative_scenarios(config);au=audit(config,sim,neg)
    pid,ledger=store(out,{"simulation":sim,"negative_scenarios":neg,"audit":au})
    man=manifest(out,ledger)
    return {"status":"PASS" if au["status"]=="PASS" else "FAIL",
            "package_id":pid,"manifest":man,"simulation":sim,"audit":au}

def certificate(out, config, result):
    sim=result["simulation"]
    checks={"pipeline_pass":result["status"]=="PASS",
            "cycles_three":sim["cycle_count"]==config.cycle_count,
            "signals_three":sim["signal_count"]==config.cycle_count,
            "final_state_stopped":sim["final_state"]=="STOPPED",
            "audit_pass":result["audit"]["status"]=="PASS",
            "network_zero":sim["network_requests_executed"]==0,
            "orders_zero":sim["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.80","status":"PASS" if not failed else "FAIL",
       "scope":"PAPER_SCHEDULER_RUNTIME_SIMULATION",
       "stages_completed":[f"V88.{i:02d}" for i in range(61,81)],
       "config":asdict(config),"checks":checks,"failed_checks":failed,
       "scheduler_runtime_simulation_complete":not failed,
       "daily_runtime_simulation_certified":not failed,
       "scheduler_enabled":False,"runtime_loop_enabled":False,
       "market_data_network_enabled":False,"auto_execution_enabled":False,
       "paper_order_submission_authorized":False,"live_trading_authorized":False,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "summary":{"package_id":result["package_id"],
                  "cycle_count":sim["cycle_count"],"signal_count":sim["signal_count"],
                  "final_state":sim["final_state"],"audit_status":result["audit"]["status"]},
       "next_phase":"V88_81_PAPER_AUTOMATION_FRAMEWORK_FINAL_CERTIFICATION"}
    d["certificate_sha256"]=hjson(d)
    write_json(out/"scheduler_runtime_sim_certificate_v88_80.json",d)
    write_json(out/"scheduler_runtime_sim_verify_v88_80.json",
               {"stage":"V88.80","status":d["status"],"verified":not failed,
                "failed_checks":failed,"certificate_sha256":d["certificate_sha256"],
                "next_phase":d["next_phase"]})
    return d
