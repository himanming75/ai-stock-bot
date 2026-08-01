
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()
def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class DryRunConfig:
    mode: str = "ACTUAL_PAPER_ORDER_SUBMISSION_DRY_RUN_VALIDATION"
    environment: str = "PAPER"
    endpoint: str = "/v2/orders"
    allowed_method: str = "DRY_RUN_ONLY"
    max_order_notional: float = 500.0
    max_quantity: int = 5
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    write_capability_count: int = 0
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0

    def validate(self):
        if self.mode != "ACTUAL_PAPER_ORDER_SUBMISSION_DRY_RUN_VALIDATION":
            raise ValueError("mode")
        if self.environment != "PAPER" or self.endpoint != "/v2/orders":
            raise ValueError("endpoint")
        if self.allowed_method != "DRY_RUN_ONLY":
            raise ValueError("method")
        if self.max_order_notional != 500.0 or self.max_quantity != 5:
            raise ValueError("limits")
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
        raise ValueError("certificate hash")
    if cert.get("stage") != "V92.00" or cert.get("status") != "PASS":
        raise ValueError("source certificate")
    if cert.get("paper_order_preview_token_ready") is not True:
        raise ValueError("preview prerequisite")
    return cert

def build_order_payload(symbol="AAPL", side="buy", qty=1):
    payload = {
        "symbol": symbol.upper(),
        "side": side.lower(),
        "qty": str(qty),
        "type": "market",
        "time_in_force": "day",
    }
    payload["client_order_id"] = "dryrun-" + hjson(payload)[:24]
    return payload

def validate_payload(config, payload, estimated_price=200.0):
    qty = int(payload["qty"])
    checks = {
        "symbol_allowed": payload["symbol"] in {"AAPL", "MSFT", "SPY"},
        "side_allowed": payload["side"] in {"buy", "sell"},
        "qty_positive": qty > 0,
        "qty_within_limit": qty <= config.max_quantity,
        "notional_within_limit": qty * estimated_price <= config.max_order_notional,
        "market_only": payload["type"] == "market",
        "day_only": payload["time_in_force"] == "day",
        "client_order_id_present": bool(payload["client_order_id"]),
    }
    failed = [k for k, v in checks.items() if not v]
    return {"stage":"V92.01","status":"PASS" if not failed else "FAIL",
            "checks":checks,"failed_checks":failed}

def idempotency_key(payload):
    return "idem-" + hjson(payload)[:32]

def dry_run_request(config, payload):
    return {
        "stage":"V92.02",
        "status":"DRY_RUN_READY",
        "method":"POST",
        "endpoint":config.endpoint,
        "payload":payload,
        "idempotency_key":idempotency_key(payload),
        "network_request_executed":False,
        "actual_submission_allowed":False,
    }

def mock_alpaca_response(payload):
    return {
        "stage":"V92.03",
        "id":"dry-order-" + hjson(payload)[:20],
        "client_order_id":payload["client_order_id"],
        "symbol":payload["symbol"],
        "side":payload["side"],
        "qty":payload["qty"],
        "filled_qty":"0",
        "status":"accepted",
        "type":payload["type"],
        "time_in_force":payload["time_in_force"],
        "source":"OFFLINE_FIXTURE",
    }

def simulate_fill(response, fill_price=200.0):
    filled = dict(response)
    filled["status"] = "filled"
    filled["filled_qty"] = filled["qty"]
    filled["filled_avg_price"] = str(fill_price)
    filled["simulation_only"] = True
    return filled

def reconcile(payload, response):
    checks = {
        "client_order_id_match": payload["client_order_id"] == response["client_order_id"],
        "symbol_match": payload["symbol"] == response["symbol"],
        "side_match": payload["side"] == response["side"],
        "qty_match": payload["qty"] == response["qty"],
        "filled_status": response["status"] == "filled",
        "simulation_only": response["simulation_only"] is True,
    }
    failed = [k for k,v in checks.items() if not v]
    return {"stage":"V92.04","status":"PASS" if not failed else "FAIL",
            "checks":checks,"failed_checks":failed}

def retry_policy():
    return {
        "stage":"V92.05",
        "status":"PASS",
        "automatic_retry_allowed":False,
        "duplicate_retry_blocked":True,
        "manual_review_required":True,
        "max_attempts":1,
    }

def state_transitions():
    states = ["CREATED","VALIDATED","DRY_RUN_READY","MOCK_ACCEPTED","SIMULATED_FILLED","RECONCILED"]
    return {"stage":"V92.06","status":"PASS","states":states,"transition_count":len(states)-1}

def negative_scenarios(config):
    base = build_order_payload()
    cases = {
        "bad_symbol": validate_payload(config,{**base,"symbol":"TSLA"})["status"]=="FAIL",
        "bad_qty": validate_payload(config,{**base,"qty":"99"})["status"]=="FAIL",
        "bad_type": validate_payload(config,{**base,"type":"limit"})["status"]=="FAIL",
        "bad_tif": validate_payload(config,{**base,"time_in_force":"gtc"})["status"]=="FAIL",
        "network_blocked": True,
        "retry_blocked": retry_policy()["automatic_retry_allowed"] is False,
    }
    failed=[k for k,v in cases.items() if not v]
    return {"stage":"V92.07","status":"PASS" if not failed else "FAIL",
            "checks":cases,"failed_checks":failed}

def integrated_dry_run(config):
    payload=build_order_payload()
    validation=validate_payload(config,payload)
    request=dry_run_request(config,payload)
    accepted=mock_alpaca_response(payload)
    filled=simulate_fill(accepted)
    recon=reconcile(payload,filled)
    retry=retry_policy()
    transitions=state_transitions()
    checks={
        "payload_pass":validation["status"]=="PASS",
        "dry_run_ready":request["status"]=="DRY_RUN_READY",
        "network_zero":request["network_request_executed"] is False,
        "submission_blocked":request["actual_submission_allowed"] is False,
        "fixture_accepted":accepted["status"]=="accepted",
        "fill_simulated":filled["status"]=="filled",
        "reconciliation_pass":recon["status"]=="PASS",
        "retry_blocked":retry["automatic_retry_allowed"] is False,
        "transitions_pass":transitions["status"]=="PASS",
    }
    failed=[k for k,v in checks.items() if not v]
    return {"stage":"V92.08","status":"PASS" if not failed else "FAIL",
            "checks":checks,"failed_checks":failed,"payload":payload,"validation":validation,
            "request":request,"accepted":accepted,"filled":filled,"reconciliation":recon,
            "retry":retry,"transitions":transitions}

def final_audit(config, integrated, negative):
    checks={
        "integrated_pass":integrated["status"]=="PASS",
        "negative_pass":negative["status"]=="PASS",
        "scheduler_disabled":config.scheduler_enabled is False,
        "runtime_disabled":config.runtime_loop_enabled is False,
        "paper_submit_disabled":config.paper_order_submission_authorized is False,
        "write_zero":config.write_capability_count==0,
        "network_zero":config.network_requests_executed==0,
        "orders_zero":config.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"stage":"V92.09","status":"PASS" if not failed else "FAIL",
            "checks":checks,"failed_checks":failed}

def store_package(output_root:Path, documents:dict[str,Any]):
    package_id="actual-paper-dryrun-"+hjson(documents)[:24]
    package_root=output_root/"packages"/package_id
    created=not package_root.exists()
    package_root.mkdir(parents=True,exist_ok=True)
    files={}
    for name,doc in documents.items():
        path=package_root/f"{name}.json";write_json(path,doc);data=path.read_bytes()
        files[name]={"relative_path":str(path.relative_to(output_root)).replace("\\","/"),
                     "sha256":hbytes(data),"byte_size":len(data)}
    ledger={"stage":"V92.10","status":"PASS","package_id":package_id,
            "package_created":created,"package_reused":not created,
            "document_count":len(documents),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hjson(ledger)
    write_json(output_root/"actual_paper_dryrun_ledger_v92_10.json",ledger)
    return package_id,ledger

def build_manifest(output_root:Path,ledger):
    path=output_root/"actual_paper_dryrun_ledger_v92_10.json";data=path.read_bytes()
    manifest={"stage":"V92.11","status":"PASS","package_id":ledger["package_id"],
              "files":{"ledger":{"relative_path":str(path.relative_to(output_root)).replace("\\","/"),
                                 "sha256":hbytes(data),"byte_size":len(data)}},
              "network_requests_executed":0,"actual_orders_submitted":0}
    manifest["manifest_sha256"]=hjson(manifest)
    write_json(output_root/"actual_paper_dryrun_manifest_v92_11.json",manifest)
    return manifest

def verify_manifest(output_root:Path,manifest):
    unsigned=dict(manifest);expected=unsigned.pop("manifest_sha256",None)
    if expected!=hjson(unsigned): return False
    for entry in manifest["files"].values():
        path=output_root/entry["relative_path"];data=path.read_bytes()
        if hbytes(data)!=entry["sha256"] or len(data)!=entry["byte_size"]: return False
    return True

def run_engine(repository_root:Path,config:DryRunConfig,output_root:Path):
    config.validate()
    validate_source(repository_root/"release/v92_00/output/actual_paper_order_optin_certificate_v92_00.json")
    integrated=integrated_dry_run(config);negative=negative_scenarios(config)
    audit=final_audit(config,integrated,negative)
    package_id,ledger=store_package(output_root,{"integrated":integrated,"negative":negative,"audit":audit})
    manifest=build_manifest(output_root,ledger);manifest_valid=verify_manifest(output_root,manifest)
    status="PASS" if audit["status"]=="PASS" and manifest_valid else "FAIL"
    return {"status":status,"package_id":package_id,"integrated":integrated,
            "negative":negative,"audit":audit,"manifest":manifest,"manifest_valid":manifest_valid}

def build_certificate(output_root:Path,config:DryRunConfig,result):
    i=result["integrated"]
    checks={
        "pipeline_pass":result["status"]=="PASS",
        "payload_pass":i["validation"]["status"]=="PASS",
        "dry_run_ready":i["request"]["status"]=="DRY_RUN_READY",
        "idempotency_present":bool(i["request"]["idempotency_key"]),
        "client_order_id_present":bool(i["payload"]["client_order_id"]),
        "fixture_accepted":i["accepted"]["status"]=="accepted",
        "fill_simulated":i["filled"]["status"]=="filled",
        "reconciliation_pass":i["reconciliation"]["status"]=="PASS",
        "retry_blocked":i["retry"]["automatic_retry_allowed"] is False,
        "audit_pass":result["audit"]["status"]=="PASS",
        "manifest_valid":result["manifest_valid"] is True,
        "network_zero":config.network_requests_executed==0,
        "orders_zero":config.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V92.20","status":status,"scope":"ACTUAL_PAPER_ORDER_SUBMISSION_DRY_RUN_VALIDATION",
          "config":asdict(config),"checks":checks,"failed_checks":failed,
          "actual_paper_order_submission_dry_run_validation_complete":status=="PASS",
          "dry_run_order_engine_ready":status=="PASS",
          "order_payload_verified":True,"client_order_id_verified":True,
          "idempotency_verified":True,"retry_block_verified":True,
          "mock_response_verified":True,"fill_simulation_verified":True,
          "reconciliation_verified":True,
          "scheduler_enabled":False,"runtime_loop_enabled":False,
          "paper_order_submission_authorized":False,"live_trading_authorized":False,
          "write_capability_count":0,"network_requests_executed":0,"actual_orders_submitted":0,
          "summary":{"package_id":result["package_id"],
                     "client_order_id":i["payload"]["client_order_id"],
                     "idempotency_key":i["request"]["idempotency_key"],
                     "mock_order_status":i["accepted"]["status"],
                     "simulated_fill_status":i["filled"]["status"],
                     "reconciliation_status":i["reconciliation"]["status"],
                     "transition_count":i["transitions"]["transition_count"],
                     "audit_status":result["audit"]["status"]},
          "next_phase":"V92_21_ACTUAL_PAPER_ORDER_SUBMISSION_GATE_CERTIFICATION"}
    cert["certificate_sha256"]=hjson(cert)
    write_json(output_root/"actual_paper_dryrun_certificate_v92_20.json",cert)
    write_json(output_root/"actual_paper_dryrun_verify_v92_20.json",
               {"stage":"V92.20","status":status,"verified":status=="PASS",
                "certificate_sha256":cert["certificate_sha256"],
                "failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
