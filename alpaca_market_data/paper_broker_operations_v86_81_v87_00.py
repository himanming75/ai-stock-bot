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
class PaperBrokerOperationsConfig:
    mode: str = "PAPER_BROKER_RC_OPERATIONS_FOUNDATION"
    environment: str = "PAPER"
    release_candidate: str = "PAPER_BROKER_NETWORK_RC1_OFFLINE"
    daily_order_limit: int = 1
    daily_notional_limit: float = 500.0
    max_open_positions: int = 3
    session_ttl_seconds: int = 900
    health_check_interval_seconds: int = 60
    require_manual_start: bool = True
    require_manual_stop: bool = True
    auto_order_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    allow_network: bool = False
    actual_orders_submitted: int = 0
    def validate(self):
        if self.mode != "PAPER_BROKER_RC_OPERATIONS_FOUNDATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if self.release_candidate != "PAPER_BROKER_NETWORK_RC1_OFFLINE": raise ValueError("release candidate")
        if self.daily_order_limit != 1 or self.daily_notional_limit <= 0: raise ValueError("daily limits")
        if self.max_open_positions < 1 or self.session_ttl_seconds < 300: raise ValueError("operations limits")
        if not self.require_manual_start or not self.require_manual_stop: raise ValueError("manual control")
        if self.auto_order_enabled or self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.allow_network or self.actual_orders_submitted != 0: raise ValueError("offline operations only")

def validate_source(path: Path) -> dict[str, Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e != hj(u) or c.get("stage")!="V86.80" or c.get("status")!="PASS":
        raise ValueError("bad V86.80 certificate")
    if c.get("paper_broker_network_certified") is not True:
        raise ValueError("network certification prerequisite")
    if c.get("paper_order_submission_authorized") is not False or c.get("live_trading_authorized") is not False:
        raise ValueError("unsafe source")
    return c

def release_policy(config):
    d={"stage":"V86.81","status":"PASS","environment":config.environment,
       "release_candidate":config.release_candidate,"promotion_authorized":False,
       "auto_order_enabled":False,"paper_order_submission_authorized":False,
       "live_trading_authorized":False}
    d["policy_sha256"]=hj(d);return d

def operations_profile(config):
    d={"stage":"V86.82","daily_order_limit":config.daily_order_limit,
       "daily_notional_limit":config.daily_notional_limit,
       "max_open_positions":config.max_open_positions,
       "session_ttl_seconds":config.session_ttl_seconds,
       "health_check_interval_seconds":config.health_check_interval_seconds,
       "manual_start_required":config.require_manual_start,
       "manual_stop_required":config.require_manual_stop}
    d["profile_sha256"]=hj(d);return d

def start_request(operator_id,reason):
    if not operator_id.strip() or not reason.strip(): raise ValueError("start request")
    d={"stage":"V86.83","request_id":"paper-ops-start-"+hj([operator_id,reason])[:20],
       "operator_id":operator_id,"reason":reason,"status":"PENDING",
       "session_started":False,"network_enabled":False}
    d["request_sha256"]=hj(d);return d

def start_gate(config,request):
    checks={"request_pending":request["status"]=="PENDING",
            "manual_start_required":config.require_manual_start,
            "auto_order_disabled":config.auto_order_enabled is False,
            "paper_submit_false":config.paper_order_submission_authorized is False,
            "live_false":config.live_trading_authorized is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.84","status":"PASS" if not failed else "FAIL","checks":checks,
       "failed_checks":failed,"session_start_authorized":not failed,
       "network_enabled":False}
    d["start_gate_sha256"]=hj(d);return d

def issue_session(config,request,gate):
    if gate["status"]!="PASS": raise ValueError("start gate")
    d={"stage":"V86.85","session_id":"paper-ops-session-"+hj([request,gate])[:24],
       "status":"READY_NOT_STARTED","ttl_seconds":config.session_ttl_seconds,
       "orders_used":0,"notional_used":0.0,"network_enabled":False,
       "order_submission_enabled":False}
    d["session_sha256"]=hj(d);return d

def health_check(session):
    checks={"session_exists":bool(session.get("session_id")),
            "network_disabled":session.get("network_enabled") is False,
            "order_submission_disabled":session.get("order_submission_enabled") is False,
            "orders_used_zero":session.get("orders_used")==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.86","status":"PASS" if not failed else "FAIL","checks":checks,
       "failed_checks":failed}
    d["health_sha256"]=hj(d);return d

def daily_limit_guard(config,orders_requested,notional_requested,open_positions):
    checks={"order_limit":0<=orders_requested<=config.daily_order_limit,
            "notional_limit":0<=notional_requested<=config.daily_notional_limit,
            "position_limit":0<=open_positions<=config.max_open_positions}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.87","status":"PASS" if not failed else "FAIL",
       "orders_requested":orders_requested,"notional_requested":notional_requested,
       "open_positions":open_positions,"checks":checks,"failed_checks":failed}
    d["limit_guard_sha256"]=hj(d);return d

def stop_request(operator_id,reason):
    if not operator_id.strip() or not reason.strip(): raise ValueError("stop request")
    d={"stage":"V86.88","request_id":"paper-ops-stop-"+hj([operator_id,reason])[:20],
       "operator_id":operator_id,"reason":reason,"status":"PENDING"}
    d["request_sha256"]=hj(d);return d

def stop_session(session,request):
    d={**session,"stage":"V86.89","status":"STOPPED",
       "stop_request_id":request["request_id"],"network_enabled":False,
       "order_submission_enabled":False}
    d["session_sha256"]=hj({k:v for k,v in d.items() if k!="session_sha256"});return d

def incident_policy():
    d={"stage":"V86.90","status":"PASS",
       "severity_levels":["INFO","WARNING","CRITICAL"],
       "critical_actions":["STOP_SESSION","REVOKE_TOKEN","DISABLE_NETWORK","ROLLBACK"],
       "automatic_order_action":False,"manual_ack_required":True}
    d["incident_policy_sha256"]=hj(d);return d

def incident_record(severity,code,message):
    if severity not in {"INFO","WARNING","CRITICAL"}: raise ValueError("severity")
    d={"stage":"V86.91","incident_id":"paper-ops-incident-"+hj([severity,code,message])[:20],
       "severity":severity,"code":code,"message":message,
       "acknowledged":False,"resolved":False}
    d["incident_sha256"]=hj(d);return d

def rollback_plan():
    d={"stage":"V86.92","status":"PASS","rollback_target":"V86.80",
       "stop_session":True,"disable_network":True,"disable_order_submission":True,
       "clear_credentials":True,"revoke_runtime_tokens":True,
       "preserve_audit_logs":True,"manual_confirmation_required":True}
    d["rollback_sha256"]=hj(d);return d

def runbook():
    steps=[
      "VERIFY_V86_80_CERTIFICATE","CHECK_GIT_STATUS_CLEAN","RUN_INSTALL_CHECK",
      "RUN_TESTS","RUN_OFFLINE_PIPELINE","VERIFY_OUTPUT","ISSUE_MANUAL_START_REQUEST",
      "CHECK_HEALTH","CHECK_DAILY_LIMITS","STOP_SESSION","ARCHIVE_REPORTS"
    ]
    d={"stage":"V86.93","status":"PASS","step_count":len(steps),"steps":steps,
       "contains_order_submission_step":False}
    d["runbook_sha256"]=hj(d);return d

def deployment_checklist(config):
    checks={"source_certificate_present":True,"release_candidate_valid":config.release_candidate.endswith("_OFFLINE"),
            "manual_start":config.require_manual_start,"manual_stop":config.require_manual_stop,
            "auto_order_disabled":config.auto_order_enabled is False,
            "paper_submit_false":config.paper_order_submission_authorized is False,
            "live_false":config.live_trading_authorized is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.94","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["checklist_sha256"]=hj(d);return d

def operations_scenario(config):
    start=start_request("operator-1","offline RC operations verification")
    gate=start_gate(config,start);session=issue_session(config,start,gate)
    health=health_check(session)
    limits_pass=daily_limit_guard(config,1,250.0,1)
    limits_fail=daily_limit_guard(config,2,1000.0,4)
    incident=incident_record("CRITICAL","OFFLINE_TEST","simulated critical incident")
    stop=stop_request("operator-1","scenario complete")
    stopped=stop_session(session,stop)
    d={"stage":"V86.95","status":"PASS","start_gate_status":gate["status"],
       "health_status":health["status"],"limit_pass_status":limits_pass["status"],
       "limit_fail_status":limits_fail["status"],"critical_incident_created":incident["severity"]=="CRITICAL",
       "session_stopped":stopped["status"]=="STOPPED",
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{"start_request":start,"start_gate":gate,"session":session,
                    "health":health,"limit_pass":limits_pass,"limit_fail":limits_fail,
                    "incident":incident,"stop_request":stop,"stopped_session":stopped}}
    d["scenario_sha256"]=hj(d);return d

def audit(config,policy,profile,scenario,incident,rollback,runbook_doc,checklist):
    checks={"policy_pass":policy["status"]=="PASS",
            "release_candidate_valid":policy["release_candidate"]==config.release_candidate,
            "profile_order_limit_one":profile["daily_order_limit"]==1,
            "start_gate_pass":scenario["start_gate_status"]=="PASS",
            "health_pass":scenario["health_status"]=="PASS",
            "positive_limit_pass":scenario["limit_pass_status"]=="PASS",
            "negative_limit_fail":scenario["limit_fail_status"]=="FAIL",
            "critical_incident_supported":scenario["critical_incident_created"],
            "session_stopped":scenario["session_stopped"],
            "incident_policy_pass":incident["status"]=="PASS",
            "rollback_pass":rollback["status"]=="PASS",
            "runbook_pass":runbook_doc["status"]=="PASS",
            "checklist_pass":checklist["status"]=="PASS",
            "network_zero":scenario["network_requests_executed"]==0,
            "orders_zero":scenario["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.96","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def operations_report(config,scenario,audit_doc):
    d={"stage":"V86.97","status":"PASS" if audit_doc["status"]=="PASS" else "FAIL",
       "release_candidate":config.release_candidate,
       "operations_mode":"OFFLINE_RC_OPERATIONS_FOUNDATION",
       "session_model":"MANUAL_START_STOP",
       "daily_order_limit":config.daily_order_limit,
       "daily_notional_limit":config.daily_notional_limit,
       "max_open_positions":config.max_open_positions,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "audit_status":audit_doc["status"]}
    d["report_sha256"]=hj(d);return d

def store(out,docs):
    pid="paper-ops-foundation-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V86.98","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"operations_ledger_v86_98.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"operations_ledger_v86_98.json";b=p.read_bytes()
    d={"stage":"V86.99","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"operations_manifest_v86_99.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_source(root/"release/v86_80/output/final_network_certificate_v86_80.json")
    pol=release_policy(c);profile=operations_profile(c);incident=incident_policy()
    rollback=rollback_plan();runbook_doc=runbook();checklist=deployment_checklist(c)
    scenario=operations_scenario(c)
    au=audit(c,pol,profile,scenario,incident,rollback,runbook_doc,checklist)
    report=operations_report(c,scenario,au)
    docs={"source_certificate":{"certificate_sha256":source["certificate_sha256"],
           "release_candidate":source["final_network_summary"]["release_candidate"]},
          "release_policy":pol,"operations_profile":profile,"incident_policy":incident,
          "rollback_plan":rollback,"runbook":runbook_doc,"deployment_checklist":checklist,
          "operations_scenario":scenario,"audit":au,"operations_report":report}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    summary={"release_candidate":c.release_candidate,
             "operations_mode":"OFFLINE_RC_OPERATIONS_FOUNDATION",
             "manual_start_required":c.require_manual_start,
             "manual_stop_required":c.require_manual_stop,
             "daily_order_limit":c.daily_order_limit,
             "daily_notional_limit":c.daily_notional_limit,
             "max_open_positions":c.max_open_positions,
             "health_status":scenario["health_status"],
             "limit_guard_negative_test":scenario["limit_fail_status"],
             "incident_response_ready":scenario["critical_incident_created"],
             "rollback_status":rollback["status"],
             "runbook_status":runbook_doc["status"],
             "checklist_status":checklist["status"],
             "audit_status":au["status"],
             "network_requests_executed":0,
             "actual_orders_submitted":0}
    return {"stage":"V87.00","status":"PASS" if au["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "manual_start_required":s["manual_start_required"],
            "manual_stop_required":s["manual_stop_required"],
            "daily_order_limit_one":s["daily_order_limit"]==1,
            "health_pass":s["health_status"]=="PASS",
            "negative_limit_test_fail":s["limit_guard_negative_test"]=="FAIL",
            "incident_ready":s["incident_response_ready"],
            "rollback_pass":s["rollback_status"]=="PASS",
            "runbook_pass":s["runbook_status"]=="PASS",
            "checklist_pass":s["checklist_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V87.00","status":status,
       "scope":"PAPER_BROKER_RELEASE_CANDIDATE_AND_OPERATIONS_FOUNDATION",
       "stages_completed":[f"V86.{i:02d}" for i in range(81,100)]+["V87.00"],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "operations_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "operations_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "paper_broker_operations_foundation_complete":status=="PASS",
       "paper_broker_release_candidate_ready":status=="PASS",
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,
       "actual_orders_submitted":0,
       "next_phase":"V87_01_PAPER_STRATEGY_EXECUTION_OPERATIONS_FOUNDATION"}
    d["certificate_sha256"]=hj(d);wj(out/"operations_certificate_v87_00.json",d)
    wj(out/"operations_verify_v87_00.json",
       {"stage":"V87.00","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
