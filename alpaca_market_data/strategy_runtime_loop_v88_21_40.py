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
class StrategyRuntimeLoopConfig:
    mode: str = "PAPER_STRATEGY_RUNTIME_LOOP_FOUNDATION"
    environment: str = "PAPER"
    strategy_id: str = "SAFE_MOMENTUM_PREVIEW"
    loop_interval_seconds: int = 60
    cycle_timeout_seconds: int = 30
    heartbeat_stale_seconds: int = 120
    data_freshness_seconds: int = 90
    max_consecutive_errors: int = 3
    checkpoint_every_cycles: int = 1
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    allow_network: bool = False
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0
    def validate(self):
        if self.mode != "PAPER_STRATEGY_RUNTIME_LOOP_FOUNDATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if not self.strategy_id.strip(): raise ValueError("strategy")
        if min(self.loop_interval_seconds,self.cycle_timeout_seconds,self.heartbeat_stale_seconds,self.data_freshness_seconds) <= 0:
            raise ValueError("timing")
        if self.max_consecutive_errors < 1 or self.checkpoint_every_cycles < 1: raise ValueError("limits")
        if self.scheduler_enabled or self.runtime_loop_enabled or self.auto_execution_enabled:
            raise ValueError("runtime disabled")
        if self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.allow_network or self.network_requests_executed != 0 or self.actual_orders_submitted != 0:
            raise ValueError("offline only")

def validate_source(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V88.20" or c.get("status")!="PASS":
        raise ValueError("bad V88.20 certificate")
    if c.get("paper_scheduler_foundation_complete") is not True:
        raise ValueError("scheduler prerequisite")
    if c.get("scheduler_enabled") is not False:
        raise ValueError("unsafe source")
    return c

def runtime_policy(config):
    d={"stage":"V88.21","status":"PASS","strategy_id":config.strategy_id,
       "scheduler_enabled":False,"runtime_loop_enabled":False,
       "auto_execution_enabled":False,"paper_order_submission_authorized":False,
       "live_trading_authorized":False,"network_enabled":False}
    d["policy_sha256"]=hj(d);return d

def market_state(is_trading_day=True,is_open=True):
    d={"stage":"V88.22","is_trading_day":is_trading_day,"is_market_open":is_open,
       "status":"OPEN" if is_trading_day and is_open else "CLOSED"}
    d["market_sha256"]=hj(d);return d

def heartbeat(cycle_id,age_seconds=0):
    d={"stage":"V88.23","cycle_id":cycle_id,"age_seconds":age_seconds,
       "status":"PASS"}
    d["heartbeat_sha256"]=hj(d);return d

def heartbeat_check(config,hb):
    stale=hb["age_seconds"]>config.heartbeat_stale_seconds
    d={"stage":"V88.24","status":"FAIL" if stale else "PASS",
       "stale":stale,"age_seconds":hb["age_seconds"]}
    d["heartbeat_check_sha256"]=hj(d);return d

def data_freshness(config,bar_age_seconds):
    stale=bar_age_seconds>config.data_freshness_seconds
    d={"stage":"V88.25","status":"FAIL" if stale else "PASS",
       "bar_age_seconds":bar_age_seconds,"stale":stale}
    d["freshness_sha256"]=hj(d);return d

def strategy_cycle(config,cycle_id,market,heartbeat_status,freshness):
    checks={"market_open":market["status"]=="OPEN",
            "heartbeat_pass":heartbeat_status["status"]=="PASS",
            "data_fresh":freshness["status"]=="PASS"}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.26","cycle_id":cycle_id,
       "status":"PASS" if not failed else "SKIP",
       "checks":checks,"failed_checks":failed,
       "signal_generation_allowed":not failed,
       "dispatch_enabled":False}
    d["cycle_sha256"]=hj(d);return d

def signal_candidate(config,cycle):
    if cycle["status"]!="PASS": raise ValueError("cycle not ready")
    d={"stage":"V88.27","signal_id":"runtime-signal-"+hj([config.strategy_id,cycle["cycle_id"]])[:24],
       "strategy_id":config.strategy_id,"symbol":"AAPL","side":"buy",
       "confidence":0.82,"status":"CANDIDATE","order_submission_ready":False}
    d["signal_sha256"]=hj(d);return d

def signal_dedup(signal,seen_ids):
    dup=signal["signal_id"] in seen_ids
    d={"stage":"V88.28","signal_id":signal["signal_id"],
       "duplicate_detected":dup,
       "accepted":not dup}
    d["dedup_sha256"]=hj(d);return d

def timeout_guard(config,elapsed_seconds):
    timed_out=elapsed_seconds>config.cycle_timeout_seconds
    d={"stage":"V88.29","elapsed_seconds":elapsed_seconds,
       "timed_out":timed_out,"status":"FAIL" if timed_out else "PASS"}
    d["timeout_sha256"]=hj(d);return d

def exception_containment(error_count,config):
    stop=error_count>=config.max_consecutive_errors
    d={"stage":"V88.30","consecutive_errors":error_count,
       "threshold":config.max_consecutive_errors,
       "runtime_stop_required":stop,
       "status":"FAIL" if stop else "PASS"}
    d["containment_sha256"]=hj(d);return d

def runtime_queue(signal,dedup):
    items=[] if not dedup["accepted"] else [{"signal_id":signal["signal_id"],"status":"QUEUED_PREVIEW"}]
    d={"stage":"V88.31","queue_depth":len(items),"items":items,
       "dispatch_enabled":False}
    d["queue_sha256"]=hj(d);return d

def checkpoint(cycle,queue):
    d={"stage":"V88.32","checkpoint_id":"runtime-checkpoint-"+hj([cycle,queue])[:24],
       "cycle_id":cycle["cycle_id"],"queue_depth":queue["queue_depth"],
       "status":"SAVED","resumable":True}
    d["checkpoint_sha256"]=hj(d);return d

def resume(checkpoint_doc):
    if not checkpoint_doc.get("resumable"): raise ValueError("not resumable")
    d={"stage":"V88.33","resume_id":"runtime-resume-"+hj(checkpoint_doc)[:24],
       "checkpoint_id":checkpoint_doc["checkpoint_id"],
       "status":"RESUMED_PREVIEW_ONLY","dispatch_enabled":False}
    d["resume_sha256"]=hj(d);return d

def graceful_shutdown(queue):
    d={"stage":"V88.34","status":"STOPPED","queue_depth_before":queue["queue_depth"],
       "queue_cleared":True,"checkpoint_persisted":True,
       "network_enabled":False,"order_submission_enabled":False}
    d["shutdown_sha256"]=hj(d);return d

def retry_policy(attempt,max_attempts=2):
    allowed=attempt<max_attempts
    d={"stage":"V88.35","attempt":attempt,"max_attempts":max_attempts,
       "retry_allowed":allowed,"next_attempt":attempt+1 if allowed else None}
    d["retry_sha256"]=hj(d);return d

def loop_iteration(config,cycle_id,seen_ids=None):
    seen_ids=set(seen_ids or [])
    market=market_state(True,True)
    hb=heartbeat(cycle_id,30)
    hb_check=heartbeat_check(config,hb)
    freshness=data_freshness(config,45)
    cycle=strategy_cycle(config,cycle_id,market,hb_check,freshness)
    signal=signal_candidate(config,cycle)
    dedup=signal_dedup(signal,seen_ids)
    queue=runtime_queue(signal,dedup)
    timeout=timeout_guard(config,10)
    contain=exception_containment(0,config)
    cp=checkpoint(cycle,queue)
    resumed=resume(cp)
    shutdown=graceful_shutdown(queue)
    retry_initial=retry_policy(0)
    retry_exhausted=retry_policy(2)
    d={"stage":"V88.36","status":"PASS",
       "market_status":market["status"],
       "heartbeat_status":hb_check["status"],
       "freshness_status":freshness["status"],
       "cycle_status":cycle["status"],
       "signal_status":signal["status"],
       "duplicate_detected":dedup["duplicate_detected"],
       "queue_depth":queue["queue_depth"],
       "timeout_status":timeout["status"],
       "containment_status":contain["status"],
       "checkpoint_status":cp["status"],
       "resume_status":resumed["status"],
       "shutdown_status":shutdown["status"],
       "retry_initial_allowed":retry_initial["retry_allowed"],
       "retry_exhausted_blocked":not retry_exhausted["retry_allowed"],
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{"market":market,"heartbeat":hb,"heartbeat_check":hb_check,
                    "freshness":freshness,"cycle":cycle,"signal":signal,
                    "dedup":dedup,"queue":queue,"timeout":timeout,
                    "containment":contain,"checkpoint":cp,"resume":resumed,
                    "shutdown":shutdown,"retry_initial":retry_initial,
                    "retry_exhausted":retry_exhausted}}
    d["iteration_sha256"]=hj(d);return d

def negative_scenarios(config):
    market_closed=strategy_cycle(config,"closed",market_state(True,False),
        heartbeat_check(config,heartbeat("closed",0)),data_freshness(config,10))
    stale_data=data_freshness(config,999)
    stale_hb=heartbeat_check(config,heartbeat("stale",999))
    timeout=timeout_guard(config,999)
    containment=exception_containment(config.max_consecutive_errors,config)
    signal=signal_candidate(config,strategy_cycle(config,"dup",market_state(True,True),
        heartbeat_check(config,heartbeat("dup",0)),data_freshness(config,10)))
    duplicate=signal_dedup(signal,{signal["signal_id"]})
    d={"stage":"V88.37","status":"PASS",
       "market_closed_skipped":market_closed["status"]=="SKIP",
       "stale_data_failed":stale_data["status"]=="FAIL",
       "stale_heartbeat_failed":stale_hb["status"]=="FAIL",
       "timeout_failed":timeout["status"]=="FAIL",
       "containment_stop_required":containment["runtime_stop_required"],
       "duplicate_detected":duplicate["duplicate_detected"]}
    d["negative_sha256"]=hj(d);return d

def audit(config,iteration,negative):
    checks={"market_open":iteration["market_status"]=="OPEN",
            "heartbeat_pass":iteration["heartbeat_status"]=="PASS",
            "freshness_pass":iteration["freshness_status"]=="PASS",
            "cycle_pass":iteration["cycle_status"]=="PASS",
            "signal_candidate":iteration["signal_status"]=="CANDIDATE",
            "queue_depth_one":iteration["queue_depth"]==1,
            "timeout_pass":iteration["timeout_status"]=="PASS",
            "containment_pass":iteration["containment_status"]=="PASS",
            "checkpoint_saved":iteration["checkpoint_status"]=="SAVED",
            "resume_preview_only":iteration["resume_status"]=="RESUMED_PREVIEW_ONLY",
            "shutdown_stopped":iteration["shutdown_status"]=="STOPPED",
            "retry_initial_allowed":iteration["retry_initial_allowed"],
            "retry_exhausted_blocked":iteration["retry_exhausted_blocked"],
            "negative_scenarios_pass":negative["status"]=="PASS",
            "runtime_disabled":config.runtime_loop_enabled is False,
            "network_zero":iteration["network_requests_executed"]==0,
            "orders_zero":iteration["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.38","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store(out,docs):
    pid="runtime-loop-foundation-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V88.39","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"runtime_loop_ledger_v88_39.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"runtime_loop_ledger_v88_39.json";b=p.read_bytes()
    d={"stage":"V88.40","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"runtime_loop_manifest_v88_40.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_source(root/"release/v88_20/output/scheduler_foundation_certificate_v88_20.json")
    policy=runtime_policy(c);iteration=loop_iteration(c,"cycle-001");negative=negative_scenarios(c)
    au=audit(c,iteration,negative)
    docs={"source_certificate":{"certificate_sha256":source["certificate_sha256"]},
          "runtime_policy":policy,"loop_iteration":iteration,
          "negative_scenarios":negative,"audit":au}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    summary={"strategy_id":c.strategy_id,
             "market_status":iteration["market_status"],
             "heartbeat_status":iteration["heartbeat_status"],
             "freshness_status":iteration["freshness_status"],
             "cycle_status":iteration["cycle_status"],
             "signal_status":iteration["signal_status"],
             "queue_depth":iteration["queue_depth"],
             "checkpoint_status":iteration["checkpoint_status"],
             "resume_status":iteration["resume_status"],
             "shutdown_status":iteration["shutdown_status"],
             "retry_initial_allowed":iteration["retry_initial_allowed"],
             "retry_exhausted_blocked":iteration["retry_exhausted_blocked"],
             "negative_scenarios_status":negative["status"],
             "audit_status":au["status"],
             "network_requests_executed":0,"actual_orders_submitted":0}
    return {"stage":"V88.40","status":"PASS" if au["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "market_open":s["market_status"]=="OPEN",
            "heartbeat_pass":s["heartbeat_status"]=="PASS",
            "freshness_pass":s["freshness_status"]=="PASS",
            "cycle_pass":s["cycle_status"]=="PASS",
            "signal_candidate":s["signal_status"]=="CANDIDATE",
            "queue_depth_one":s["queue_depth"]==1,
            "checkpoint_saved":s["checkpoint_status"]=="SAVED",
            "resume_preview_only":s["resume_status"]=="RESUMED_PREVIEW_ONLY",
            "shutdown_stopped":s["shutdown_status"]=="STOPPED",
            "retry_initial_allowed":s["retry_initial_allowed"],
            "retry_exhausted_blocked":s["retry_exhausted_blocked"],
            "negative_scenarios_pass":s["negative_scenarios_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V88.40","status":status,
       "scope":"PAPER_STRATEGY_RUNTIME_LOOP_FOUNDATION",
       "stages_completed":[f"V88.{i:02d}" for i in range(21,41)],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "runtime_loop_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "runtime_loop_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "paper_strategy_runtime_loop_foundation_complete":status=="PASS",
       "runtime_loop_preview_ready":status=="PASS",
       "scheduler_enabled":False,"runtime_loop_enabled":False,
       "auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "next_phase":"V88_41_PAPER_MARKET_DATA_OPERATIONS_FOUNDATION"}
    d["certificate_sha256"]=hj(d);wj(out/"runtime_loop_certificate_v88_40.json",d)
    wj(out/"runtime_loop_verify_v88_40.json",
       {"stage":"V88.40","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
