
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import hashlib, json, os, ssl, time

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()
def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class ActualPaperAutomationConfig:
    mode: str = "ACTUAL_PAPER_AUTOMATION_ENABLEMENT_FOUNDATION"
    environment: str = "PAPER"
    provider: str = "ALPACA"
    base_url: str = "https://paper-api.alpaca.markets"
    account_path: str = "/v2/account"
    clock_path: str = "/v2/clock"
    calendar_path: str = "/v2/calendar"
    timeout_seconds: int = 10
    max_retries: int = 1
    network_opt_in_env: str = "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ"
    api_key_env: str = "APCA_API_KEY_ID"
    api_secret_env: str = "APCA_API_SECRET_KEY"
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    write_capability_count: int = 0

    def validate(self):
        if self.mode != "ACTUAL_PAPER_AUTOMATION_ENABLEMENT_FOUNDATION": raise ValueError("mode")
        if self.environment != "PAPER" or self.provider != "ALPACA": raise ValueError("environment/provider")
        if self.base_url != "https://paper-api.alpaca.markets": raise ValueError("paper endpoint only")
        if self.timeout_seconds <= 0 or self.max_retries < 0: raise ValueError("network settings")
        if any([self.scheduler_enabled,self.runtime_loop_enabled,self.auto_execution_enabled,
                self.paper_order_submission_authorized,self.live_trading_authorized]):
            raise ValueError("unsafe enablement")
        if self.write_capability_count != 0: raise ValueError("write capability")

def validate_source(path: Path) -> dict[str,Any]:
    c=json.loads(path.read_text(encoding="utf-8"))
    u=dict(c); expected=u.pop("certificate_sha256")
    if expected != hjson(u): raise ValueError("certificate hash")
    if c.get("stage")!="V90.00" or c.get("status")!="PASS": raise ValueError("source certificate")
    if c.get("paper_runtime_rc1_ready") is not True: raise ValueError("RC1 prerequisite")
    if c.get("paper_order_submission_authorized") is not False: raise ValueError("unsafe source")
    return c

def endpoint_catalog(config):
    endpoints=[
      {"name":"account","method":"GET","path":config.account_path,"capability":"READ_ACCOUNT"},
      {"name":"clock","method":"GET","path":config.clock_path,"capability":"READ_CLOCK"},
      {"name":"calendar","method":"GET","path":config.calendar_path,"capability":"READ_CALENDAR"},
    ]
    d={"status":"PASS","endpoint_count":3,"read_capability_count":3,
       "write_capability_count":0,"endpoints":endpoints}
    d["sha256"]=hjson(d);return d

def credentials_from_env(config, env=None):
    env=env or os.environ
    key=env.get(config.api_key_env,"").strip()
    secret=env.get(config.api_secret_env,"").strip()
    present=bool(key and secret)
    return {"present":present,"api_key":key if present else "",
            "api_secret":secret if present else "",
            "redacted_key":(key[:4]+"..."+key[-4:]) if len(key)>=8 else ("***" if key else ""),
            "redacted_secret":"***" if secret else ""}

def network_opted_in(config, env=None):
    env=env or os.environ
    return env.get(config.network_opt_in_env,"").strip().upper()=="YES"

def build_headers(credentials):
    if not credentials["present"]: raise ValueError("missing credentials")
    return {"APCA-API-KEY-ID":credentials["api_key"],
            "APCA-API-SECRET-KEY":credentials["api_secret"],
            "Accept":"application/json","User-Agent":"ai-stock-bot-readonly-v90"}

def validate_request(method, url, config):
    if method.upper() != "GET": raise ValueError("GET only")
    if not url.startswith(config.base_url+"/v2/"): raise ValueError("paper v2 endpoint only")
    blocked=("/orders","/positions/","/assets/")
    if any(x in url for x in blocked): raise ValueError("endpoint not in read-only catalog")
    allowed={config.base_url+config.account_path,config.base_url+config.clock_path}
    if not (url in allowed or url.startswith(config.base_url+config.calendar_path)):
        raise ValueError("endpoint not allowed")
    return True

def default_transport(method, url, headers, timeout):
    req=Request(url=url,method=method,headers=headers)
    ctx=ssl.create_default_context()
    with urlopen(req,timeout=timeout,context=ctx) as resp:
        return {"status_code":int(resp.status),
                "body":json.loads(resp.read().decode("utf-8"))}

def read_endpoint(config, name, credentials, transport=default_transport):
    catalog={e["name"]:e for e in endpoint_catalog(config)["endpoints"]}
    if name not in catalog: raise ValueError("unknown endpoint")
    ep=catalog[name]
    url=config.base_url+ep["path"]
    if name=="calendar": url += "?start=2026-01-01&end=2026-12-31"
    validate_request(ep["method"],url,config)
    headers=build_headers(credentials)
    last_error=None
    for attempt in range(config.max_retries+1):
        try:
            result=transport("GET",url,headers,config.timeout_seconds)
            return {"name":name,"status":"PASS","status_code":result["status_code"],
                    "payload":result["body"],"attempt_count":attempt+1}
        except Exception as exc:
            last_error=exc
            if attempt<config.max_retries: time.sleep(0)
    return {"name":name,"status":"FAIL","error":type(last_error).__name__,
            "message":str(last_error),"attempt_count":config.max_retries+1}

def validate_account(payload):
    required=["status","cash","buying_power","portfolio_value","equity","trading_blocked"]
    checks={"required_fields":all(k in payload for k in required),
            "status_present":bool(str(payload.get("status",""))),
            "numeric_fields":all(_is_number(payload.get(k)) for k in ["cash","buying_power","portfolio_value","equity"]),
            "trading_blocked_boolean":isinstance(payload.get("trading_blocked"),bool)}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}

def _is_number(v):
    try: float(v); return True
    except (TypeError,ValueError): return False

def validate_clock(payload):
    required=["timestamp","is_open","next_open","next_close"]
    checks={"required_fields":all(k in payload for k in required),
            "is_open_boolean":isinstance(payload.get("is_open"),bool),
            "timestamps_present":all(bool(str(payload.get(k,""))) for k in ["timestamp","next_open","next_close"])}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}

def validate_calendar(payload):
    rows=payload if isinstance(payload,list) else []
    checks={"is_list":isinstance(payload,list),"rows_present":len(rows)>0,
            "required_fields":all(all(k in row for k in ["date","open","close"]) for row in rows)}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
            "session_count":len(rows)}

def mock_transport(method,url,headers,timeout):
    if url.endswith("/v2/account"):
        body={"status":"ACTIVE","cash":"100000","buying_power":"400000",
              "portfolio_value":"100000","equity":"100000","trading_blocked":False}
    elif url.endswith("/v2/clock"):
        body={"timestamp":"2026-07-06T10:00:00-04:00","is_open":True,
              "next_open":"2026-07-07T09:30:00-04:00","next_close":"2026-07-06T16:00:00-04:00"}
    elif "/v2/calendar?" in url:
        body=[{"date":"2026-07-06","open":"09:30","close":"16:00"},
              {"date":"2026-07-07","open":"09:30","close":"16:00"}]
    else: raise ValueError("unexpected URL")
    return {"status_code":200,"body":body}

def offline_scenario(config):
    credentials={"present":True,"api_key":"MOCK_KEY","api_secret":"MOCK_SECRET"}
    account=read_endpoint(config,"account",credentials,mock_transport)
    clock=read_endpoint(config,"clock",credentials,mock_transport)
    calendar=read_endpoint(config,"calendar",credentials,mock_transport)
    av=validate_account(account["payload"]);cv=validate_clock(clock["payload"])
    calv=validate_calendar(calendar["payload"])
    checks={"account_read_pass":account["status"]=="PASS",
            "clock_read_pass":clock["status"]=="PASS",
            "calendar_read_pass":calendar["status"]=="PASS",
            "account_schema_pass":av["status"]=="PASS",
            "clock_schema_pass":cv["status"]=="PASS",
            "calendar_schema_pass":calv["status"]=="PASS",
            "write_capabilities_zero":config.write_capability_count==0}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
            "account":account,"clock":clock,"calendar":calendar,
            "account_validation":av,"clock_validation":cv,"calendar_validation":calv,
            "network_mode":"OFFLINE_FIXTURE","network_requests_executed":0,
            "actual_orders_submitted":0}

def actual_read_scenario(config, env=None, transport=default_transport):
    if not network_opted_in(config,env): raise ValueError("actual paper read opt-in required")
    credentials=credentials_from_env(config,env)
    if not credentials["present"]: raise ValueError("paper credentials required")
    results={name:read_endpoint(config,name,credentials,transport)
             for name in ["account","clock","calendar"]}
    validators={
      "account":validate_account(results["account"].get("payload",{})),
      "clock":validate_clock(results["clock"].get("payload",{})),
      "calendar":validate_calendar(results["calendar"].get("payload",[])),
    }
    checks={f"{name}_read_pass":results[name]["status"]=="PASS" for name in results}
    checks.update({f"{name}_schema_pass":validators[name]["status"]=="PASS" for name in validators})
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
            "results":results,"validations":validators,
            "credentials_present":True,
            "redacted_key":credentials["redacted_key"],
            "network_mode":"ACTUAL_PAPER_READ_ONLY",
            "network_requests_executed":sum(1 for r in results.values() if r["status"]=="PASS"),
            "actual_orders_submitted":0}

def safety_tests(config):
    blocked={}
    for label,method,url in [
      ("post_order","POST",config.base_url+"/v2/orders"),
      ("get_order","GET",config.base_url+"/v2/orders/abc"),
      ("live_endpoint","GET","https://api.alpaca.markets/v2/account"),
      ("unknown_endpoint","GET",config.base_url+"/v2/assets"),
    ]:
        try:
            validate_request(method,url,config);blocked[label]=False
        except ValueError:
            blocked[label]=True
    return {"status":"PASS" if all(blocked.values()) else "FAIL","blocked":blocked}

def audit(config, scenario, safety):
    checks={"scenario_pass":scenario["status"]=="PASS",
            "safety_pass":safety["status"]=="PASS",
            "write_capability_zero":config.write_capability_count==0,
            "scheduler_disabled":config.scheduler_enabled is False,
            "runtime_disabled":config.runtime_loop_enabled is False,
            "auto_execution_disabled":config.auto_execution_enabled is False,
            "paper_submit_disabled":config.paper_order_submission_authorized is False,
            "live_disabled":config.live_trading_authorized is False,
            "orders_zero":scenario["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}

def store(out,docs):
    pid="actual-paper-read-foundation-"+hjson(docs)[:24]
    package=out/"packages"/pid;package.mkdir(parents=True,exist_ok=True)
    files={}
    for name,doc in docs.items():
        p=package/f"{name}.json";write_json(p,doc);b=p.read_bytes()
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hbytes(b),"byte_size":len(b)}
    ledger={"status":"PASS","package_id":pid,"document_count":len(docs),"files":files,
            "actual_orders_submitted":0}
    ledger["ledger_sha256"]=hjson(ledger);write_json(out/"actual_paper_read_ledger_v90_20.json",ledger)
    return pid,ledger

def manifest(out,ledger):
    p=out/"actual_paper_read_ledger_v90_20.json";b=p.read_bytes()
    d={"status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hbytes(b),"byte_size":len(b)}},
       "actual_orders_submitted":0}
    d["manifest_sha256"]=hjson(d);write_json(out/"actual_paper_read_manifest_v90_20.json",d);return d

def run_engine(root,config,out):
    config.validate();validate_source(root/"release/v90_00/output/fast_track_certificate_v90_00.json")
    scenario=offline_scenario(config);safety=safety_tests(config);au=audit(config,scenario,safety)
    pid,ledger=store(out,{"endpoint_catalog":endpoint_catalog(config),
                          "offline_scenario":scenario,"safety":safety,"audit":au})
    man=manifest(out,ledger)
    return {"status":"PASS" if au["status"]=="PASS" else "FAIL",
            "package_id":pid,"scenario":scenario,"safety":safety,"audit":au,"manifest":man}

def certificate(out,config,result):
    s=result["scenario"]
    checks={"pipeline_pass":result["status"]=="PASS",
            "account_pass":s["account_validation"]["status"]=="PASS",
            "clock_pass":s["clock_validation"]["status"]=="PASS",
            "calendar_pass":s["calendar_validation"]["status"]=="PASS",
            "safety_pass":result["safety"]["status"]=="PASS",
            "audit_pass":result["audit"]["status"]=="PASS",
            "write_capabilities_zero":config.write_capability_count==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V90.20","status":"PASS" if not failed else "FAIL",
       "scope":"ACTUAL_PAPER_AUTOMATION_ENABLEMENT_FOUNDATION",
       "config":asdict(config),"checks":checks,"failed_checks":failed,
       "actual_paper_automation_enablement_foundation_complete":not failed,
       "actual_paper_read_only_ready":not failed,
       "scheduler_enabled":False,"runtime_loop_enabled":False,
       "auto_execution_enabled":False,"paper_order_submission_authorized":False,
       "live_trading_authorized":False,"write_capability_count":0,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "summary":{"package_id":result["package_id"],"endpoint_count":3,
                  "read_capability_count":3,"write_capability_count":0,
                  "account_status":s["account_validation"]["status"],
                  "clock_status":s["clock_validation"]["status"],
                  "calendar_status":s["calendar_validation"]["status"],
                  "audit_status":result["audit"]["status"]},
       "next_phase":"V90_21_ACTUAL_PAPER_READ_ONLY_RUNTIME_VALIDATION"}
    d["certificate_sha256"]=hjson(d)
    write_json(out/"actual_paper_automation_certificate_v90_20.json",d)
    write_json(out/"actual_paper_automation_verify_v90_20.json",
      {"stage":"V90.20","status":d["status"],"verified":not failed,
       "failed_checks":failed,"certificate_sha256":d["certificate_sha256"],
       "next_phase":d["next_phase"]})
    return d
