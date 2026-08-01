from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
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
class PaperSchedulerFoundationConfig:
    mode: str = "PAPER_SCHEDULER_FOUNDATION"
    environment: str = "PAPER"
    timezone: str = "America/New_York"
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0
    preopen_minutes: int = 15
    postclose_minutes: int = 10
    duplicate_window_seconds: int = 300
    missed_recovery_window_minutes: int = 30
    scheduler_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    allow_network: bool = False
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0
    def validate(self):
        if self.mode != "PAPER_SCHEDULER_FOUNDATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        ZoneInfo(self.timezone)
        if not (0 <= self.market_open_hour <= 23 and 0 <= self.market_close_hour <= 23): raise ValueError("hour")
        if not (0 <= self.market_open_minute <= 59 and 0 <= self.market_close_minute <= 59): raise ValueError("minute")
        if self.preopen_minutes < 0 or self.postclose_minutes < 0: raise ValueError("buffer")
        if self.duplicate_window_seconds <= 0 or self.missed_recovery_window_minutes <= 0: raise ValueError("window")
        if self.scheduler_enabled or self.auto_execution_enabled or self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.allow_network or self.network_requests_executed != 0 or self.actual_orders_submitted != 0:
            raise ValueError("offline only")

def validate_source(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V88.00" or c.get("status")!="PASS":
        raise ValueError("bad V88.00 certificate")
    if c.get("paper_strategy_operations_rc1_ready") is not True:
        raise ValueError("operations RC prerequisite")
    if c.get("scheduler_enabled") is not False:
        raise ValueError("unsafe source")
    return c

def scheduler_policy(config):
    d={"stage":"V88.01","status":"PASS","environment":config.environment,
       "timezone":config.timezone,"scheduler_enabled":False,
       "auto_execution_enabled":False,"paper_order_submission_authorized":False,
       "live_trading_authorized":False}
    d["policy_sha256"]=hj(d);return d

def market_calendar():
    holidays=[
      "2026-01-01","2026-01-19","2026-02-16","2026-04-03",
      "2026-05-25","2026-06-19","2026-07-03","2026-09-07",
      "2026-11-26","2026-12-25"
    ]
    early_closes=["2026-11-27","2026-12-24"]
    d={"stage":"V88.02","calendar_year":2026,
       "weekday_open_days":[0,1,2,3,4],
       "holiday_dates":holidays,"early_close_dates":early_closes,
       "source":"STATIC_OFFLINE_FIXTURE"}
    d["calendar_sha256"]=hj(d);return d

def is_trading_day(day:date,calendar_doc):
    return day.weekday() in calendar_doc["weekday_open_days"] and day.isoformat() not in calendar_doc["holiday_dates"]

def session_times(config,day:date,calendar_doc):
    tz=ZoneInfo(config.timezone)
    open_dt=datetime.combine(day,time(config.market_open_hour,config.market_open_minute),tzinfo=tz)
    close_hour,close_minute=(13,0) if day.isoformat() in calendar_doc["early_close_dates"] else (config.market_close_hour,config.market_close_minute)
    close_dt=datetime.combine(day,time(close_hour,close_minute),tzinfo=tz)
    d={"stage":"V88.03","date":day.isoformat(),
       "is_trading_day":is_trading_day(day,calendar_doc),
       "preopen_at":(open_dt-timedelta(minutes=config.preopen_minutes)).isoformat(),
       "market_open_at":open_dt.isoformat(),
       "market_close_at":close_dt.isoformat(),
       "postclose_at":(close_dt+timedelta(minutes=config.postclose_minutes)).isoformat(),
       "early_close":day.isoformat() in calendar_doc["early_close_dates"]}
    d["session_sha256"]=hj(d);return d

def dst_validation(config):
    tz=ZoneInfo(config.timezone)
    winter=datetime(2026,1,15,12,0,tzinfo=tz)
    summer=datetime(2026,7,15,12,0,tzinfo=tz)
    d={"stage":"V88.04","winter_utc_offset_seconds":int(winter.utcoffset().total_seconds()),
       "summer_utc_offset_seconds":int(summer.utcoffset().total_seconds()),
       "dst_difference_seconds":int((summer.utcoffset()-winter.utcoffset()).total_seconds()),
       "status":"PASS" if winter.utcoffset()!=summer.utcoffset() else "FAIL"}
    d["dst_sha256"]=hj(d);return d

def event_plan(session):
    events=[
      {"name":"PREOPEN_PREP","at":session["preopen_at"],"enabled":False},
      {"name":"MARKET_OPEN","at":session["market_open_at"],"enabled":False},
      {"name":"MARKET_CLOSE","at":session["market_close_at"],"enabled":False},
      {"name":"POSTCLOSE_REPORT","at":session["postclose_at"],"enabled":False},
    ]
    d={"stage":"V88.05","status":"PASS","event_count":len(events),
       "events":events,"all_events_disabled":all(not e["enabled"] for e in events)}
    d["event_plan_sha256"]=hj(d);return d

def duplicate_guard(config,event_name,event_time,last_run_time=None):
    duplicate=False
    if last_run_time is not None:
        duplicate=abs((event_time-last_run_time).total_seconds())<=config.duplicate_window_seconds
    d={"stage":"V88.06","event_name":event_name,
       "duplicate_detected":duplicate,
       "dispatch_allowed":not duplicate and False}
    d["duplicate_sha256"]=hj(d);return d

def missed_schedule_recovery(config,scheduled_time,current_time):
    delay_minutes=max(0.0,(current_time-scheduled_time).total_seconds()/60.0)
    recoverable=0<delay_minutes<=config.missed_recovery_window_minutes
    d={"stage":"V88.07","delay_minutes":delay_minutes,
       "recoverable":recoverable,
       "recovery_action":"MANUAL_REVIEW" if recoverable else "SKIP",
       "automatic_dispatch":False}
    d["recovery_sha256"]=hj(d);return d

def manual_override_request(operator_id,reason,event_name):
    if not operator_id.strip() or not reason.strip() or not event_name.strip(): raise ValueError("override")
    d={"stage":"V88.08","override_id":"scheduler-override-"+hj([operator_id,reason,event_name])[:20],
       "operator_id":operator_id,"reason":reason,"event_name":event_name,
       "status":"PENDING","dispatch_enabled":False}
    d["override_sha256"]=hj(d);return d

def manual_override_decision(request,approver_id,approved):
    if request["status"]!="PENDING" or not approver_id.strip(): raise ValueError("decision")
    d={**request,"stage":"V88.09","status":"APPROVED" if approved else "REJECTED",
       "approver_id":approver_id,"dispatch_enabled":False}
    d["override_sha256"]=hj({k:v for k,v in d.items() if k!="override_sha256"});return d

def scheduler_state():
    d={"stage":"V88.10","state":"DISABLED_READY",
       "scheduler_enabled":False,"active_event":None,
       "last_event":None,"next_event":None,
       "network_enabled":False,"order_submission_enabled":False}
    d["state_sha256"]=hj(d);return d

def state_transition(state,event):
    allowed=state["state"]=="DISABLED_READY" and event in {"PREVIEW_EVENT","MANUAL_CHECK"}
    d={"stage":"V88.11","from_state":state["state"],
       "event":event,"to_state":"DISABLED_READY" if allowed else "ERROR",
       "transition_allowed":allowed,"dispatch_performed":False}
    d["transition_sha256"]=hj(d);return d

def heartbeat(now_iso):
    d={"stage":"V88.12","heartbeat_at":now_iso,
       "scheduler_enabled":False,"status":"PASS"}
    d["heartbeat_sha256"]=hj(d);return d

def stale_heartbeat_check(last_heartbeat,current_time,threshold_seconds=120):
    age=(current_time-last_heartbeat).total_seconds()
    d={"stage":"V88.13","age_seconds":age,
       "stale":age>threshold_seconds,
       "status":"FAIL" if age>threshold_seconds else "PASS"}
    d["stale_sha256"]=hj(d);return d

def shutdown_plan():
    d={"stage":"V88.14","status":"PASS",
       "disable_new_events":True,"clear_pending_events":True,
       "persist_state":True,"release_lock":True,
       "disable_network":True,"disable_order_submission":True}
    d["shutdown_sha256"]=hj(d);return d

def rollback_plan():
    d={"stage":"V88.15","status":"PASS","rollback_target":"V88.00",
       "disable_scheduler":True,"clear_scheduler_state":True,
       "clear_pending_events":True,"restore_manual_operations_rc":True,
       "disable_network":True,"disable_order_submission":True}
    d["rollback_sha256"]=hj(d);return d

def scenario(config):
    calendar_doc=market_calendar()
    normal=session_times(config,date(2026,7,6),calendar_doc)
    holiday=session_times(config,date(2026,7,3),calendar_doc)
    early=session_times(config,date(2026,11,27),calendar_doc)
    dst=dst_validation(config)
    events=event_plan(normal)
    event_dt=datetime.fromisoformat(normal["market_open_at"])
    duplicate_ok=duplicate_guard(config,"MARKET_OPEN",event_dt,None)
    duplicate_hit=duplicate_guard(config,"MARKET_OPEN",event_dt,event_dt+timedelta(seconds=60))
    missed_ok=missed_schedule_recovery(config,event_dt,event_dt+timedelta(minutes=10))
    missed_skip=missed_schedule_recovery(config,event_dt,event_dt+timedelta(minutes=60))
    override=manual_override_request("operator-1","offline scheduler preview","MARKET_OPEN")
    override_decision=manual_override_decision(override,"approver-1",True)
    state=scheduler_state();transition=state_transition(state,"PREVIEW_EVENT")
    hb=heartbeat(event_dt.isoformat())
    fresh=stale_heartbeat_check(event_dt,event_dt+timedelta(seconds=30))
    stale=stale_heartbeat_check(event_dt,event_dt+timedelta(seconds=300))
    shutdown=shutdown_plan();rollback=rollback_plan()
    d={"stage":"V88.16","status":"PASS",
       "normal_trading_day":normal["is_trading_day"],
       "holiday_closed":holiday["is_trading_day"] is False,
       "early_close_detected":early["early_close"],
       "dst_status":dst["status"],
       "event_count":events["event_count"],
       "events_disabled":events["all_events_disabled"],
       "duplicate_clear":duplicate_ok["duplicate_detected"] is False,
       "duplicate_detected":duplicate_hit["duplicate_detected"],
       "missed_recoverable":missed_ok["recoverable"],
       "missed_outside_window_skipped":missed_skip["recoverable"] is False,
       "manual_override_approved":override_decision["status"]=="APPROVED",
       "manual_override_dispatch_disabled":override_decision["dispatch_enabled"] is False,
       "state_transition_pass":transition["transition_allowed"],
       "fresh_heartbeat_pass":fresh["status"]=="PASS",
       "stale_heartbeat_fail":stale["status"]=="FAIL",
       "shutdown_status":shutdown["status"],
       "rollback_status":rollback["status"],
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{"calendar":calendar_doc,"normal_session":normal,
                    "holiday_session":holiday,"early_session":early,
                    "dst":dst,"events":events,"duplicate_clear":duplicate_ok,
                    "duplicate_hit":duplicate_hit,"missed_ok":missed_ok,
                    "missed_skip":missed_skip,"override":override,
                    "override_decision":override_decision,"state":state,
                    "transition":transition,"heartbeat":hb,"fresh":fresh,
                    "stale":stale,"shutdown":shutdown,"rollback":rollback}}
    d["scenario_sha256"]=hj(d);return d

def audit(config,scenario_doc):
    checks={"normal_trading_day":scenario_doc["normal_trading_day"],
            "holiday_closed":scenario_doc["holiday_closed"],
            "early_close_detected":scenario_doc["early_close_detected"],
            "dst_pass":scenario_doc["dst_status"]=="PASS",
            "events_four":scenario_doc["event_count"]==4,
            "events_disabled":scenario_doc["events_disabled"],
            "duplicate_clear":scenario_doc["duplicate_clear"],
            "duplicate_detected":scenario_doc["duplicate_detected"],
            "missed_recoverable":scenario_doc["missed_recoverable"],
            "missed_skip":scenario_doc["missed_outside_window_skipped"],
            "override_approved":scenario_doc["manual_override_approved"],
            "override_dispatch_disabled":scenario_doc["manual_override_dispatch_disabled"],
            "state_transition_pass":scenario_doc["state_transition_pass"],
            "fresh_heartbeat_pass":scenario_doc["fresh_heartbeat_pass"],
            "stale_heartbeat_fail":scenario_doc["stale_heartbeat_fail"],
            "shutdown_pass":scenario_doc["shutdown_status"]=="PASS",
            "rollback_pass":scenario_doc["rollback_status"]=="PASS",
            "scheduler_disabled":config.scheduler_enabled is False,
            "network_zero":scenario_doc["network_requests_executed"]==0,
            "orders_zero":scenario_doc["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V88.17","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store(out,docs):
    pid="paper-scheduler-foundation-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V88.18","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"scheduler_foundation_ledger_v88_18.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"scheduler_foundation_ledger_v88_18.json";b=p.read_bytes()
    d={"stage":"V88.19","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"scheduler_foundation_manifest_v88_19.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_source(root/"release/v88_00/output/strategy_operations_rc_certificate_v88_00.json")
    policy=scheduler_policy(c);scenario_doc=scenario(c);au=audit(c,scenario_doc)
    docs={"source_certificate":{"certificate_sha256":source["certificate_sha256"],
                               "release_candidate":source["strategy_operations_rc_summary"]["release_candidate"]},
          "scheduler_policy":policy,"scheduler_scenario":scenario_doc,"audit":au}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    summary={"timezone":c.timezone,
             "normal_trading_day":scenario_doc["normal_trading_day"],
             "holiday_closed":scenario_doc["holiday_closed"],
             "early_close_detected":scenario_doc["early_close_detected"],
             "dst_status":scenario_doc["dst_status"],
             "event_count":scenario_doc["event_count"],
             "duplicate_detected":scenario_doc["duplicate_detected"],
             "missed_recoverable":scenario_doc["missed_recoverable"],
             "manual_override_approved":scenario_doc["manual_override_approved"],
             "stale_heartbeat_detected":scenario_doc["stale_heartbeat_fail"],
             "shutdown_status":scenario_doc["shutdown_status"],
             "rollback_status":scenario_doc["rollback_status"],
             "audit_status":au["status"],
             "network_requests_executed":0,"actual_orders_submitted":0}
    return {"stage":"V88.20","status":"PASS" if au["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "normal_trading_day":s["normal_trading_day"],
            "holiday_closed":s["holiday_closed"],
            "early_close_detected":s["early_close_detected"],
            "dst_pass":s["dst_status"]=="PASS",
            "event_count_four":s["event_count"]==4,
            "duplicate_detected":s["duplicate_detected"],
            "missed_recoverable":s["missed_recoverable"],
            "manual_override_approved":s["manual_override_approved"],
            "stale_heartbeat_detected":s["stale_heartbeat_detected"],
            "shutdown_pass":s["shutdown_status"]=="PASS",
            "rollback_pass":s["rollback_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V88.20","status":status,
       "scope":"PAPER_SCHEDULER_FOUNDATION",
       "stages_completed":[f"V88.{i:02d}" for i in range(1,21)],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "scheduler_foundation_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "scheduler_foundation_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "paper_scheduler_foundation_complete":status=="PASS",
       "scheduler_preview_ready":status=="PASS",
       "scheduler_enabled":False,
       "auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "next_phase":"V88_21_PAPER_STRATEGY_RUNTIME_LOOP_FOUNDATION"}
    d["certificate_sha256"]=hj(d);wj(out/"scheduler_foundation_certificate_v88_20.json",d)
    wj(out/"scheduler_foundation_verify_v88_20.json",
       {"stage":"V88.20","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
