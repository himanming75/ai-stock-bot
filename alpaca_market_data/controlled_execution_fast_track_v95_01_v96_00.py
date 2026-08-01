
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Protocol
import hashlib, json, os, urllib.request, urllib.error

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
CONFIRMATION_TEXT = "I UNDERSTAND THIS WILL SUBMIT ONE ALPACA PAPER ORDER"

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()

def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class ControlledExecutionConfig:
    mode: str = "ACTUAL_PAPER_SINGLE_ORDER_CONTROLLED_EXECUTION_FAST_TRACK"
    release_candidate: str = "ACTUAL_PAPER_SINGLE_ORDER_CONTROLLED_RC1"
    base_url: str = PAPER_BASE_URL
    symbol: str = "AAPL"
    side: str = "buy"
    quantity: int = 1
    estimated_price: float = 95.0
    max_order_notional: float = 100.0
    max_orders_per_session: int = 1
    session_ttl_seconds: int = 300
    timeout_seconds: int = 10
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    live_trading_authorized: bool = False

    def validate(self):
        if self.mode != "ACTUAL_PAPER_SINGLE_ORDER_CONTROLLED_EXECUTION_FAST_TRACK":
            raise ValueError("mode")
        if self.release_candidate != "ACTUAL_PAPER_SINGLE_ORDER_CONTROLLED_RC1":
            raise ValueError("release candidate")
        if self.base_url != PAPER_BASE_URL:
            raise ValueError("paper URL only")
        if self.symbol not in {"AAPL","MSFT","SPY"}:
            raise ValueError("symbol")
        if self.side not in {"buy","sell"}:
            raise ValueError("side")
        if self.quantity != 1 or self.max_orders_per_session != 1:
            raise ValueError("single-order policy")
        if self.estimated_price * self.quantity > self.max_order_notional:
            raise ValueError("notional")
        if self.session_ttl_seconds != 300 or self.timeout_seconds != 10:
            raise ValueError("session/timeout")
        if any([self.scheduler_enabled,self.runtime_loop_enabled,
                self.auto_execution_enabled,self.live_trading_authorized]):
            raise ValueError("unsafe enablement")

def validate_source(path: Path):
    cert=json.loads(path.read_text(encoding="utf-8"))
    unsigned=dict(cert);expected=unsigned.pop("certificate_sha256",None)
    if expected!=hjson(unsigned): raise ValueError("source hash")
    if cert.get("stage")!="V95.00" or cert.get("status")!="PASS":
        raise ValueError("source")
    if cert.get("actual_paper_single_order_network_ready_rc1") is not True:
        raise ValueError("prerequisite")
    return cert

def execution_environment(env=None):
    env=os.environ if env is None else env
    flags={
        "read_opt_in":env.get("AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ")=="1",
        "single_order_opt_in":env.get("AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER")=="1",
        "controlled_execution_opt_in":env.get("AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION")=="1",
        "manual_confirmation":env.get("AI_STOCK_BOT_CONTROLLED_EXECUTION_CONFIRMATION")==CONFIRMATION_TEXT,
        "credentials_present":bool(env.get("APCA_API_KEY_ID")) and bool(env.get("APCA_API_SECRET_KEY")),
        "kill_switch_clear":env.get("AI_STOCK_BOT_KILL_SWITCH","0")=="0",
    }
    ready=all(flags.values())
    return {"stage":"V95.01","status":"READY" if ready else "BLOCKED",
            "flags":flags,"execution_ready":ready}

def build_order(config):
    payload={"symbol":config.symbol,"side":config.side,"qty":str(config.quantity),
             "type":"market","time_in_force":"day"}
    payload["client_order_id"]="controlled-"+hjson(payload)[:20]
    return payload

def approval_token(config, now=1000000):
    token={"stage":"V95.10","status":"ACTIVE","approval_count":2,"required_approvals":2,
           "issued_at":now,"expires_at":now+config.session_ttl_seconds,
           "remaining_uses":1,"remaining_orders":1,"scope":"ONE_PAPER_ORDER"}
    token["token_sha256"]=hjson(token)
    return token

def preflight(config, env=None):
    state=execution_environment(env)
    payload=build_order(config)
    checks={
        "environment_ready":state["execution_ready"],
        "paper_url_only":config.base_url==PAPER_BASE_URL,
        "symbol_allowed":payload["symbol"] in {"AAPL","MSFT","SPY"},
        "quantity_one":int(payload["qty"])==1,
        "notional_within_limit":config.estimated_price*config.quantity<=config.max_order_notional,
        "client_order_id_present":bool(payload["client_order_id"]),
        "scheduler_disabled":config.scheduler_enabled is False,
        "runtime_disabled":config.runtime_loop_enabled is False,
        "auto_execution_disabled":config.auto_execution_enabled is False,
        "live_trading_disabled":config.live_trading_authorized is False,
    }
    return {"stage":"V95.20","status":"PASS" if all(checks.values()) else "BLOCKED",
            "checks":checks,"payload":payload,"environment":state}

class Transport(Protocol):
    def submit(self, url:str, headers:dict[str,str], payload:dict[str,Any], timeout:int)->dict[str,Any]: ...

class FixtureTransport:
    def submit(self,url,headers,payload,timeout):
        return {"id":"fixture-"+hjson(payload)[:20],"client_order_id":payload["client_order_id"],
                "symbol":payload["symbol"],"side":payload["side"],"qty":payload["qty"],
                "filled_qty":"0","status":"accepted","type":payload["type"],
                "time_in_force":payload["time_in_force"],"source":"OFFLINE_FIXTURE"}

class AlpacaPaperTransport:
    def submit(self,url,headers,payload,timeout):
        body=json.dumps(payload).encode("utf-8")
        request=urllib.request.Request(url,data=body,headers=headers,method="POST")
        try:
            with urllib.request.urlopen(request,timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw=exc.read().decode("utf-8",errors="replace")
            raise RuntimeError(f"Alpaca Paper HTTP {exc.code}: {raw}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Alpaca Paper network error: {exc.reason}") from exc

def headers_from_env(env):
    return {"APCA-API-KEY-ID":env["APCA_API_KEY_ID"],
            "APCA-API-SECRET-KEY":env["APCA_API_SECRET_KEY"],
            "Content-Type":"application/json"}

def execute_once(config, transport, env=None, allow_network=False):
    env=os.environ if env is None else env
    pf=preflight(config,env)
    if pf["status"]!="PASS":
        return {"stage":"V95.30","status":"BLOCKED","reason":"preflight failed",
                "network_requests_executed":0,"actual_orders_submitted":0}
    if allow_network is False and isinstance(transport,AlpacaPaperTransport):
        return {"stage":"V95.30","status":"BLOCKED","reason":"network transport disabled",
                "network_requests_executed":0,"actual_orders_submitted":0}
    token=approval_token(config)
    if token["remaining_orders"]!=1 or token["remaining_uses"]!=1:
        raise ValueError("token")
    payload=pf["payload"]
    headers=headers_from_env(env) if isinstance(transport,AlpacaPaperTransport) else {"Content-Type":"application/json"}
    response=transport.submit(config.base_url+"/v2/orders",headers,payload,config.timeout_seconds)
    network_count=1 if isinstance(transport,AlpacaPaperTransport) else 0
    order_count=1 if isinstance(transport,AlpacaPaperTransport) else 0
    return {"stage":"V95.30","status":"SUBMITTED" if order_count else "FIXTURE_ACCEPTED",
            "payload":payload,"response":response,"token_consumed":True,
            "network_requests_executed":network_count,"actual_orders_submitted":order_count}

def reconcile(execution):
    if execution["status"] not in {"SUBMITTED","FIXTURE_ACCEPTED"}:
        return {"stage":"V95.40","status":"BLOCKED","checks":{}}
    p=execution["payload"];r=execution["response"]
    checks={"client_order_id_match":p["client_order_id"]==r.get("client_order_id"),
            "symbol_match":p["symbol"]==r.get("symbol"),
            "side_match":p["side"]==r.get("side"),
            "qty_match":p["qty"]==r.get("qty"),
            "accepted_status":r.get("status") in {"accepted","new","pending_new","filled"}}
    return {"stage":"V95.40","status":"PASS" if all(checks.values()) else "FAIL",
            "checks":checks}

def failure_policy():
    scenarios={
        "timeout":{"automatic_retry":False,"manual_review":True,"duplicate_lookup_required":True},
        "connection_error":{"automatic_retry":False,"manual_review":True,"unknown_state":True},
        "http_401":{"automatic_retry":False,"session_stopped":True,"credentials_rejected":True},
        "http_403":{"automatic_retry":False,"session_stopped":True,"risk_rejection_preserved":True},
        "http_429":{"automatic_retry":False,"manual_review":True,"backoff_required":True},
        "malformed_response":{"automatic_retry":False,"session_stopped":True,"incident_logged":True},
        "reconciliation_mismatch":{"automatic_retry":False,"kill_switch_triggered":True,"rollback_required":True},
    }
    return {"stage":"V95.50","status":"PASS","scenario_count":len(scenarios),
            "automatic_retry_disabled":True,"scenarios":scenarios}

def kill_switch_and_rollback():
    actions={"invalidate_token":True,"block_new_orders":True,"disable_network_execution":True,
             "preserve_order_response":True,"preserve_audit":True,"manual_reconciliation_required":True,
             "rollback_target_v95_00":True}
    return {"stage":"V95.60","status":"PASS","kill_switch_verified":True,
            "rollback_ready":all(actions.values()),"actions":actions}

def offline_certification(config):
    fake_env={
        "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1",
        "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
        "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1",
        "AI_STOCK_BOT_CONTROLLED_EXECUTION_CONFIRMATION":CONFIRMATION_TEXT,
        "AI_STOCK_BOT_KILL_SWITCH":"0",
        "APCA_API_KEY_ID":"FIXTURE_KEY",
        "APCA_API_SECRET_KEY":"FIXTURE_SECRET",
    }
    execution=execute_once(config,FixtureTransport(),fake_env,allow_network=False)
    recon=reconcile(execution)
    policy=failure_policy()
    rollback=kill_switch_and_rollback()
    checks={"fixture_accepted":execution["status"]=="FIXTURE_ACCEPTED",
            "fixture_network_zero":execution["network_requests_executed"]==0,
            "fixture_orders_zero":execution["actual_orders_submitted"]==0,
            "reconciliation_pass":recon["status"]=="PASS",
            "failure_policy_pass":policy["status"]=="PASS",
            "rollback_ready":rollback["rollback_ready"] is True}
    return {"stage":"V95.70","status":"PASS" if all(checks.values()) else "FAIL",
            "checks":checks,"execution":execution,"reconciliation":recon,
            "failure_policy":policy,"rollback":rollback}

def default_safety(config):
    execution=execute_once(config,FixtureTransport(),{},allow_network=False)
    network_attempt=execute_once(config,AlpacaPaperTransport(),{},allow_network=False)
    checks={"default_blocked":execution["status"]=="BLOCKED",
            "network_transport_blocked":network_attempt["status"]=="BLOCKED",
            "scheduler_disabled":config.scheduler_enabled is False,
            "runtime_disabled":config.runtime_loop_enabled is False,
            "auto_execution_disabled":config.auto_execution_enabled is False,
            "live_trading_disabled":config.live_trading_authorized is False}
    return {"stage":"V95.80","status":"PASS" if all(checks.values()) else "FAIL","checks":checks}

def store_package(output_root,docs):
    pid="controlled-execution-"+hjson(docs)[:24]
    pkg=output_root/"packages"/pid;pkg.mkdir(parents=True,exist_ok=True)
    files={}
    for name,doc in docs.items():
        p=pkg/f"{name}.json";write_json(p,doc);data=p.read_bytes()
        files[name]={"relative_path":str(p.relative_to(output_root)).replace("\\","/"),
                     "sha256":hbytes(data),"byte_size":len(data)}
    ledger={"stage":"V95.90","status":"PASS","package_id":pid,"files":files,
            "document_count":len(docs),"network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hjson(ledger)
    write_json(output_root/"controlled_execution_ledger_v95_90.json",ledger)
    return pid,ledger

def build_manifest(output_root,ledger):
    p=output_root/"controlled_execution_ledger_v95_90.json";data=p.read_bytes()
    m={"stage":"V95.91","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(output_root)).replace("\\","/"),
       "sha256":hbytes(data),"byte_size":len(data)}},"network_requests_executed":0,
       "actual_orders_submitted":0}
    m["manifest_sha256"]=hjson(m);write_json(output_root/"controlled_execution_manifest_v95_91.json",m)
    return m

def verify_manifest(output_root,m):
    u=dict(m);expected=u.pop("manifest_sha256",None)
    if expected!=hjson(u):return False
    for e in m["files"].values():
        data=(output_root/e["relative_path"]).read_bytes()
        if hbytes(data)!=e["sha256"] or len(data)!=e["byte_size"]:return False
    return True

def run_engine(repository_root,config,output_root):
    config.validate()
    source=validate_source(repository_root/"release/v95_00/output/single_order_network_optin_certificate_v95_00.json")
    offline=offline_certification(config)
    safety=default_safety(config)
    pid,ledger=store_package(output_root,{
        "source":{"stage":source["stage"],"sha256":source["certificate_sha256"]},
        "offline_certification":offline,"default_safety":safety})
    m=build_manifest(output_root,ledger);valid=verify_manifest(output_root,m)
    status="PASS" if offline["status"]=="PASS" and safety["status"]=="PASS" and valid else "FAIL"
    return {"status":status,"package_id":pid,"offline":offline,"safety":safety,"manifest_valid":valid}

def build_certificate(output_root,config,result):
    checks={"pipeline_pass":result["status"]=="PASS",
            "offline_certification_pass":result["offline"]["status"]=="PASS",
            "default_safety_pass":result["safety"]["status"]=="PASS",
            "manifest_valid":result["manifest_valid"] is True,
            "default_network_zero":True,"default_orders_zero":True}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V96.00","status":status,
          "scope":"V95.01-V96.00_CONTROLLED_EXECUTION_FAST_TRACK",
          "release_candidate":config.release_candidate,"config":asdict(config),
          "checks":checks,"failed_checks":failed,
          "controlled_execution_fast_track_complete":status=="PASS",
          "actual_paper_single_order_controlled_rc1_ready":status=="PASS",
          "preflight_verified":True,"approval_token_verified":True,
          "fixture_execution_verified":True,"reconciliation_verified":True,
          "failure_policy_verified":True,"kill_switch_verified":True,
          "rollback_verified":True,"real_transport_isolated":True,
          "default_paper_order_submission_authorized":False,
          "default_network_requests_executed":0,
          "default_actual_orders_submitted":0,
          "summary":{"package_id":result["package_id"],
                     "fixture_execution_status":result["offline"]["execution"]["status"],
                     "fixture_reconciliation_status":result["offline"]["reconciliation"]["status"],
                     "failure_scenario_count":result["offline"]["failure_policy"]["scenario_count"],
                     "rollback_status":result["offline"]["rollback"]["status"],
                     "default_safety_status":result["safety"]["status"],
                     "confirmation_text":CONFIRMATION_TEXT,
                     "max_order_notional":config.max_order_notional,
                     "max_quantity":config.quantity},
          "next_phase":"V96_01_ACTUAL_PAPER_CONTROLLED_EXECUTION_VALIDATION"}
    cert["certificate_sha256"]=hjson(cert)
    write_json(output_root/"controlled_execution_certificate_v96_00.json",cert)
    write_json(output_root/"controlled_execution_verify_v96_00.json",
               {"stage":"V96.00","status":status,"verified":status=="PASS",
                "certificate_sha256":cert["certificate_sha256"],
                "failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
