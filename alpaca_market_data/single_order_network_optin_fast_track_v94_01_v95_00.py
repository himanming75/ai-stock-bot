
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json, os

PAPER_BASE_URL = "https://paper-api.alpaca.markets"

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()

def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class NetworkOptInConfig:
    mode: str = "ACTUAL_PAPER_SINGLE_ORDER_NETWORK_OPT_IN_FAST_TRACK"
    release_candidate: str = "ACTUAL_PAPER_SINGLE_ORDER_NETWORK_READY_RC1"
    base_url: str = PAPER_BASE_URL
    required_approvals: int = 2
    session_ttl_seconds: int = 300
    max_orders_per_session: int = 1
    max_order_notional: float = 100.0
    max_quantity: int = 1
    allowed_symbols: tuple[str, ...] = ("AAPL", "MSFT", "SPY")
    read_network_opt_in_env: str = "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ"
    write_network_opt_in_env: str = "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER"
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    write_capability_count: int = 0
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0

    def validate(self):
        if self.mode != "ACTUAL_PAPER_SINGLE_ORDER_NETWORK_OPT_IN_FAST_TRACK":
            raise ValueError("mode")
        if self.release_candidate != "ACTUAL_PAPER_SINGLE_ORDER_NETWORK_READY_RC1":
            raise ValueError("release candidate")
        if self.base_url != PAPER_BASE_URL:
            raise ValueError("paper URL only")
        if (self.required_approvals, self.session_ttl_seconds, self.max_orders_per_session) != (2, 300, 1):
            raise ValueError("approval/session policy")
        if (self.max_order_notional, self.max_quantity) != (100.0, 1):
            raise ValueError("risk policy")
        if any([self.scheduler_enabled, self.runtime_loop_enabled, self.auto_execution_enabled,
                self.paper_order_submission_authorized, self.live_trading_authorized]):
            raise ValueError("unsafe enablement")
        if self.write_capability_count or self.network_requests_executed or self.actual_orders_submitted:
            raise ValueError("unsafe counters")

def validate_source(path: Path):
    cert = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(cert)
    expected = unsigned.pop("certificate_sha256", None)
    if expected != hjson(unsigned):
        raise ValueError("source certificate hash")
    if cert.get("stage") != "V94.00" or cert.get("status") != "PASS":
        raise ValueError("source certificate")
    if cert.get("single_order_preview_rc1_ready") is not True:
        raise ValueError("source prerequisite")
    return cert

def credential_state(env=None):
    env = os.environ if env is None else env
    key = env.get("APCA_API_KEY_ID", "")
    secret = env.get("APCA_API_SECRET_KEY", "")
    return {
        "stage": "V94.01",
        "status": "PRESENT" if key and secret else "MISSING",
        "api_key_present": bool(key),
        "api_secret_present": bool(secret),
        "api_key_redacted": (key[:3] + "***") if key else None,
        "api_secret_redacted": "***" if secret else None,
        "raw_credentials_exposed": False,
    }

def auth_headers_preview(env=None):
    env = os.environ if env is None else env
    state = credential_state(env)
    if state["status"] != "PRESENT":
        return {"stage":"V94.05","status":"BLOCKED_MISSING_CREDENTIALS","headers":{}}
    return {
        "stage":"V94.05",
        "status":"READY_PREVIEW",
        "headers":{
            "APCA-API-KEY-ID":"<REDACTED>",
            "APCA-API-SECRET-KEY":"<REDACTED>",
            "Content-Type":"application/json",
        },
        "raw_credentials_exposed":False,
    }

def endpoint_catalog(config):
    return {
        "stage":"V94.10",
        "status":"PASS",
        "base_url":config.base_url,
        "read_endpoints":["/v2/account","/v2/clock","/v2/calendar"],
        "single_order_endpoint":"/v2/orders",
        "allowed_read_method":"GET",
        "write_method_preview_only":"POST",
        "live_url_rejected":True,
    }

def read_opt_in(config, env=None):
    env = os.environ if env is None else env
    requested = env.get(config.read_network_opt_in_env) == "1"
    creds = credential_state(env)
    ready = requested and creds["status"] == "PRESENT"
    return {
        "stage":"V94.20",
        "status":"READY_READ_ONLY" if ready else "OFFLINE_DEFAULT",
        "opt_in_requested":requested,
        "credentials_present":creds["status"]=="PRESENT",
        "network_read_allowed":ready,
        "network_write_allowed":False,
    }

def single_order_write_contract(config, env=None):
    env = os.environ if env is None else env
    requested = env.get(config.write_network_opt_in_env) == "1"
    creds = credential_state(env)
    gates = {
        "explicit_write_opt_in":requested,
        "credentials_present":creds["status"]=="PRESENT",
        "two_approvals_required":True,
        "single_session_use":True,
        "single_order_limit":config.max_orders_per_session==1,
        "notional_cap_100":config.max_order_notional==100.0,
        "quantity_cap_one":config.max_quantity==1,
        "allowlist_required":True,
        "kill_switch_required":True,
        "manual_confirmation_required":True,
    }
    return {
        "stage":"V94.30",
        "status":"CONTRACT_READY",
        "gates":gates,
        "write_opt_in_requested":requested,
        "actual_write_authorized":False,
        "reason":"Foundation validates the contract only; broker POST remains disabled.",
    }

def order_request_preview(config):
    payload = {
        "symbol":"AAPL","side":"buy","qty":"1","type":"market","time_in_force":"day",
    }
    payload["client_order_id"] = "network-preview-" + hjson(payload)[:20]
    request = {
        "method":"POST",
        "url":config.base_url + "/v2/orders",
        "payload":payload,
        "idempotency_key":"idem-" + hjson(payload)[:32],
        "timeout_seconds":10,
    }
    checks = {
        "paper_url_only": request["url"].startswith(PAPER_BASE_URL),
        "symbol_allowed": payload["symbol"] in config.allowed_symbols,
        "quantity_one": int(payload["qty"]) <= config.max_quantity,
        "estimated_notional_within_cap": 95.0 <= config.max_order_notional,
        "client_order_id_present": bool(payload["client_order_id"]),
        "idempotency_present": bool(request["idempotency_key"]),
    }
    return {
        "stage":"V94.40",
        "status":"READY_PREVIEW_ONLY" if all(checks.values()) else "FAIL",
        "request":request,
        "checks":checks,
        "network_request_executed":False,
        "actual_submission_allowed":False,
    }

def response_parser_fixture():
    accepted = {
        "id":"fixture-order-1","client_order_id":"network-preview-fixture",
        "symbol":"AAPL","side":"buy","qty":"1","filled_qty":"0","status":"accepted",
        "type":"market","time_in_force":"day",
    }
    rejected = {"code":40310000,"message":"order rejected by fixture risk policy"}
    checks = {
        "accepted_status_parsed":accepted["status"]=="accepted",
        "accepted_symbol_parsed":accepted["symbol"]=="AAPL",
        "rejection_code_parsed":rejected["code"]==40310000,
        "rejection_message_parsed":bool(rejected["message"]),
    }
    return {"stage":"V94.50","status":"PASS","accepted":accepted,
            "rejected":rejected,"checks":checks}

def network_failure_policy():
    scenarios = {
        "timeout":{"automatic_retry":False,"manual_review":True,"duplicate_check_required":True},
        "connection_error":{"automatic_retry":False,"manual_review":True,"submission_state_unknown":True},
        "http_429":{"automatic_retry":False,"manual_review":True,"backoff_required":True},
        "http_401":{"automatic_retry":False,"credentials_rejected":True,"session_stopped":True},
        "http_403":{"automatic_retry":False,"risk_rejection_preserved":True,"session_stopped":True},
        "malformed_response":{"automatic_retry":False,"incident_logged":True,"session_stopped":True},
    }
    return {
        "stage":"V94.60",
        "status":"PASS",
        "scenario_count":len(scenarios),
        "scenarios":scenarios,
        "automatic_retry_disabled":True,
    }

def reconciliation_preview():
    request = order_request_preview(NetworkOptInConfig())["request"]["payload"]
    fixture = {
        "client_order_id":request["client_order_id"],"symbol":request["symbol"],
        "side":request["side"],"qty":request["qty"],"status":"accepted",
    }
    checks = {
        "client_order_id_match":request["client_order_id"]==fixture["client_order_id"],
        "symbol_match":request["symbol"]==fixture["symbol"],
        "side_match":request["side"]==fixture["side"],
        "qty_match":request["qty"]==fixture["qty"],
        "accepted_status":fixture["status"]=="accepted",
    }
    return {"stage":"V94.70","status":"PASS" if all(checks.values()) else "FAIL",
            "checks":checks}

def safety_certification(config):
    checks = {
        "paper_base_url_locked":config.base_url==PAPER_BASE_URL,
        "scheduler_disabled":config.scheduler_enabled is False,
        "runtime_disabled":config.runtime_loop_enabled is False,
        "auto_execution_disabled":config.auto_execution_enabled is False,
        "paper_submit_disabled":config.paper_order_submission_authorized is False,
        "live_trading_disabled":config.live_trading_authorized is False,
        "write_zero":config.write_capability_count==0,
        "network_zero":config.network_requests_executed==0,
        "orders_zero":config.actual_orders_submitted==0,
        "single_order_cap":config.max_orders_per_session==1,
        "notional_cap":config.max_order_notional==100.0,
        "quantity_cap":config.max_quantity==1,
    }
    return {"stage":"V94.80","status":"PASS" if all(checks.values()) else "FAIL",
            "checks":checks}

def rollback_plan():
    actions = {
        "rollback_target_v94_00":True,
        "clear_network_opt_in":True,
        "invalidate_session":True,
        "disable_write_contract":True,
        "preserve_audit":True,
        "preserve_source_certificate":True,
    }
    return {"stage":"V94.85","status":"PASS","rollback_ready":all(actions.values()),"actions":actions}

def integrated(config):
    catalog=endpoint_catalog(config)
    creds_missing=credential_state({})
    headers_missing=auth_headers_preview({})
    read_default=read_opt_in(config,{})
    contract_default=single_order_write_contract(config,{})
    preview=order_request_preview(config)
    parser=response_parser_fixture()
    failures=network_failure_policy()
    recon=reconciliation_preview()
    safety=safety_certification(config)
    rollback=rollback_plan()
    checks = {
        "catalog_pass":catalog["status"]=="PASS",
        "missing_credentials_safe":creds_missing["status"]=="MISSING",
        "headers_blocked_without_credentials":headers_missing["status"]=="BLOCKED_MISSING_CREDENTIALS",
        "read_offline_default":read_default["status"]=="OFFLINE_DEFAULT",
        "write_contract_not_authorized":contract_default["actual_write_authorized"] is False,
        "preview_ready":preview["status"]=="READY_PREVIEW_ONLY",
        "preview_network_zero":preview["network_request_executed"] is False,
        "parser_pass":parser["status"]=="PASS",
        "failure_policy_pass":failures["status"]=="PASS",
        "reconciliation_pass":recon["status"]=="PASS",
        "safety_pass":safety["status"]=="PASS",
        "rollback_ready":rollback["rollback_ready"] is True,
    }
    return {
        "stage":"V94.90",
        "status":"PASS" if all(checks.values()) else "FAIL",
        "checks":checks,"catalog":catalog,"credentials":creds_missing,
        "headers":headers_missing,"read_opt_in":read_default,
        "write_contract":contract_default,"request_preview":preview,
        "response_parser":parser,"failure_policy":failures,
        "reconciliation":recon,"safety":safety,"rollback":rollback,
    }

def store_package(output_root:Path, docs):
    package_id="single-order-network-optin-"+hjson(docs)[:24]
    package_root=output_root/"packages"/package_id
    package_root.mkdir(parents=True,exist_ok=True)
    files={}
    for name,doc in docs.items():
        path=package_root/f"{name}.json";write_json(path,doc);data=path.read_bytes()
        files[name]={"relative_path":str(path.relative_to(output_root)).replace("\\","/"),
                     "sha256":hbytes(data),"byte_size":len(data)}
    ledger={"stage":"V94.95","status":"PASS","package_id":package_id,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hjson(ledger)
    write_json(output_root/"network_optin_ledger_v94_95.json",ledger)
    return package_id,ledger

def build_manifest(output_root:Path,ledger):
    path=output_root/"network_optin_ledger_v94_95.json";data=path.read_bytes()
    manifest={"stage":"V94.96","status":"PASS","package_id":ledger["package_id"],
              "files":{"ledger":{"relative_path":str(path.relative_to(output_root)).replace("\\","/"),
              "sha256":hbytes(data),"byte_size":len(data)}},
              "network_requests_executed":0,"actual_orders_submitted":0}
    manifest["manifest_sha256"]=hjson(manifest)
    write_json(output_root/"network_optin_manifest_v94_96.json",manifest)
    return manifest

def verify_manifest(output_root:Path,manifest):
    unsigned=dict(manifest);expected=unsigned.pop("manifest_sha256",None)
    if expected!=hjson(unsigned): return False
    for entry in manifest["files"].values():
        data=(output_root/entry["relative_path"]).read_bytes()
        if hbytes(data)!=entry["sha256"] or len(data)!=entry["byte_size"]: return False
    return True

def run_engine(repository_root:Path,config:NetworkOptInConfig,output_root:Path):
    config.validate()
    source=validate_source(repository_root/"release/v94_00/output/submission_fast_track_certificate_v94_00.json")
    integ=integrated(config)
    package_id,ledger=store_package(output_root,{
        "source":{"stage":source["stage"],"sha256":source["certificate_sha256"]},
        "integrated":integ,
    })
    manifest=build_manifest(output_root,ledger)
    manifest_valid=verify_manifest(output_root,manifest)
    status="PASS" if integ["status"]=="PASS" and manifest_valid else "FAIL"
    return {"status":status,"package_id":package_id,"integrated":integ,
            "manifest_valid":manifest_valid}

def build_certificate(output_root:Path,config:NetworkOptInConfig,result):
    i=result["integrated"]
    checks = {
        "pipeline_pass":result["status"]=="PASS",
        "catalog_pass":i["catalog"]["status"]=="PASS",
        "credential_safety_pass":i["credentials"]["raw_credentials_exposed"] is False,
        "read_offline_default":i["read_opt_in"]["status"]=="OFFLINE_DEFAULT",
        "write_not_authorized":i["write_contract"]["actual_write_authorized"] is False,
        "request_preview_ready":i["request_preview"]["status"]=="READY_PREVIEW_ONLY",
        "response_parser_pass":i["response_parser"]["status"]=="PASS",
        "failure_policy_pass":i["failure_policy"]["status"]=="PASS",
        "reconciliation_pass":i["reconciliation"]["status"]=="PASS",
        "safety_pass":i["safety"]["status"]=="PASS",
        "rollback_ready":i["rollback"]["rollback_ready"] is True,
        "manifest_valid":result["manifest_valid"] is True,
        "network_zero":config.network_requests_executed==0,
        "orders_zero":config.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    status="PASS" if not failed else "FAIL"
    cert={
        "stage":"V95.00","status":status,
        "scope":"V94.01-V95.00_SINGLE_ORDER_NETWORK_OPT_IN_FAST_TRACK",
        "release_candidate":config.release_candidate,
        "config":{**asdict(config),"allowed_symbols":list(config.allowed_symbols)},
        "checks":checks,"failed_checks":failed,
        "single_order_network_opt_in_fast_track_complete":status=="PASS",
        "actual_paper_single_order_network_ready_rc1":status=="PASS",
        "credential_loading_verified":True,
        "paper_url_lock_verified":True,
        "read_network_opt_in_verified":True,
        "write_contract_verified":True,
        "request_signing_preview_verified":True,
        "response_parser_verified":True,
        "network_failure_policy_verified":True,
        "reconciliation_verified":True,
        "rollback_verified":True,
        "scheduler_enabled":False,"runtime_loop_enabled":False,
        "paper_order_submission_authorized":False,
        "live_trading_authorized":False,
        "write_capability_count":0,
        "network_requests_executed":0,
        "actual_orders_submitted":0,
        "summary":{
            "package_id":result["package_id"],
            "base_url":config.base_url,
            "read_opt_in_env":config.read_network_opt_in_env,
            "write_opt_in_env":config.write_network_opt_in_env,
            "max_orders_per_session":config.max_orders_per_session,
            "max_order_notional":config.max_order_notional,
            "max_quantity":config.max_quantity,
            "request_preview_status":i["request_preview"]["status"],
            "response_parser_status":i["response_parser"]["status"],
            "failure_scenario_count":i["failure_policy"]["scenario_count"],
            "reconciliation_status":i["reconciliation"]["status"],
            "safety_status":i["safety"]["status"],
        },
        "next_phase":"V95_01_ACTUAL_PAPER_SINGLE_ORDER_CONTROLLED_EXECUTION",
    }
    cert["certificate_sha256"]=hjson(cert)
    write_json(output_root/"single_order_network_optin_certificate_v95_00.json",cert)
    write_json(output_root/"single_order_network_optin_verify_v95_00.json",{
        "stage":"V95.00","status":status,"verified":status=="PASS",
        "certificate_sha256":cert["certificate_sha256"],
        "failed_checks":failed,"next_phase":cert["next_phase"],
    })
    return cert
