from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class BrokerConnectionValidationConfig:
    mode:str="OFFLINE_CONNECTION_VALIDATION"
    provider:str="ALPACA_COMPATIBLE"
    endpoint_scheme:str="https"
    timeout_seconds:int=10
    retry_limit:int=3
    rate_limit_per_minute:int=200
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="OFFLINE_CONNECTION_VALIDATION": raise ValueError("safe mode")
        if self.provider!="ALPACA_COMPATIBLE" or self.endpoint_scheme!="https": raise ValueError("provider endpoint")
        if self.timeout_seconds<1 or self.retry_limit<0 or self.rate_limit_per_minute<1: raise ValueError("limits")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline validation only")

def validate_read_only_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V82.40" or c.get("status")!="PASS": raise ValueError("bad V82.40 certificate")
    if c.get("broker_read_only_foundation_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("read only prerequisite")
    return c

def endpoint_contract()->dict[str,Any]:
    endpoints={
      "account":{"method":"GET","path":"/v2/account","write":False},
      "positions":{"method":"GET","path":"/v2/positions","write":False},
      "orders":{"method":"GET","path":"/v2/orders","write":False},
      "clock":{"method":"GET","path":"/v2/clock","write":False},
      "assets":{"method":"GET","path":"/v2/assets","write":False},
      "quotes":{"method":"GET","path":"/v2/stocks/quotes/latest","write":False},
    }
    d={"stage":"V82.41","status":"PASS","endpoint_count":len(endpoints),"endpoints":endpoints,
       "write_endpoint_count":sum(1 for x in endpoints.values() if x["write"])}
    d["endpoint_sha256"]=hj(d);return d

def validate_endpoint_contract(contract):
    checks={"endpoint_count_six":contract["endpoint_count"]==6,
      "all_get":all(x["method"]=="GET" for x in contract["endpoints"].values()),
      "write_endpoints_zero":contract["write_endpoint_count"]==0,
      "all_paths_versioned":all(x["path"].startswith("/v2/") for x in contract["endpoints"].values())}
    return _result("V82.42",checks)

def credential_shape_fixture()->dict[str,Any]:
    d={"stage":"V82.43","fields":["key_id","secret_key"],"values_loaded":False,
       "environment_variables_read":False,"credentials_used":0,"redaction_required":True}
    d["credential_shape_sha256"]=hj(d);return d

def validate_credential_shape(doc):
    checks={"two_fields":doc["fields"]==["key_id","secret_key"],"values_not_loaded":doc["values_loaded"] is False,
      "env_not_read":doc["environment_variables_read"] is False,"credentials_zero":doc["credentials_used"]==0,
      "redaction_required":doc["redaction_required"] is True}
    return _result("V82.44",checks)

def timeout_policy(config):
    d={"stage":"V82.45","connect_timeout_seconds":config.timeout_seconds,
       "read_timeout_seconds":config.timeout_seconds,"write_timeout_seconds":0,
       "network_execution_authorized":False}
    d["timeout_sha256"]=hj(d);return d

def retry_policy(config):
    d={"stage":"V82.46","maximum_attempts":config.retry_limit,
       "backoff_seconds":[2**i for i in range(config.retry_limit)],
       "retryable_classes":["TIMEOUT","RATE_LIMIT","TEMPORARY_UNAVAILABLE"],
       "network_execution_authorized":False}
    d["retry_sha256"]=hj(d);return d

def rate_limit_policy(config):
    d={"stage":"V82.47","limit_per_minute":config.rate_limit_per_minute,
       "test_request_count":0,"within_limit":True,"network_requests_executed":0}
    d["rate_limit_sha256"]=hj(d);return d

def heartbeat_fixture():
    d={"stage":"V82.48","status_code":200,"latency_ms":42,"service":"broker-read-only",
       "healthy":True,"source":"OFFLINE_FIXTURE"}
    d["heartbeat_sha256"]=hj(d);return d

def response_schema_contract():
    schemas={
      "account":["account_id","status","currency","cash","equity","buying_power"],
      "position":["symbol","quantity","average_entry_price","market_price","market_value"],
      "order":["order_id","symbol","side","quantity","status"],
      "clock":["is_open","timestamp","next_open","next_close"],
      "asset":["symbol","tradable","fractionable","shortable"],
      "quote":["symbol","bid","ask","last"],
    }
    d={"stage":"V82.49","schema_count":len(schemas),"schemas":schemas}
    d["schema_sha256"]=hj(d);return d

def sample_responses():
    return {
      "account":{"account_id":"fixture","status":"ACTIVE","currency":"USD","cash":10000.0,"equity":100000.0,"buying_power":20000.0},
      "position":{"symbol":"AAPL","quantity":10,"average_entry_price":180.0,"market_price":190.0,"market_value":1900.0},
      "order":{"order_id":"ord-1","symbol":"AAPL","side":"BUY","quantity":10,"status":"FILLED"},
      "clock":{"is_open":False,"timestamp":"2026-07-31T15:30:00-07:00","next_open":"2026-08-03T06:30:00-07:00","next_close":"2026-08-03T13:00:00-07:00"},
      "asset":{"symbol":"AAPL","tradable":True,"fractionable":True,"shortable":True},
      "quote":{"symbol":"AAPL","bid":189.95,"ask":190.05,"last":190.0},
    }

def validate_response_schemas(contract,samples):
    checks={}
    for name,fields in contract["schemas"].items():
        checks[f"{name}_schema_complete"]=all(field in samples[name] for field in fields)
    return _result("V82.50",checks)

def error_classification():
    mapping={
      "401":{"class":"AUTH","retryable":False},
      "403":{"class":"AUTHORIZATION","retryable":False},
      "404":{"class":"ENDPOINT","retryable":False},
      "408":{"class":"TIMEOUT","retryable":True},
      "429":{"class":"RATE_LIMIT","retryable":True},
      "500":{"class":"SERVER","retryable":True},
      "503":{"class":"TEMPORARY_UNAVAILABLE","retryable":True},
    }
    d={"stage":"V82.51","mapping":mapping,"error_code_count":len(mapping)}
    d["error_map_sha256"]=hj(d);return d

def validate_error_classification(doc):
    checks={"codes_positive":doc["error_code_count"]>=7,
      "auth_not_retryable":not doc["mapping"]["401"]["retryable"],
      "rate_limit_retryable":doc["mapping"]["429"]["retryable"],
      "server_retryable":doc["mapping"]["500"]["retryable"]}
    return _result("V82.52",checks)

def tls_contract():
    d={"stage":"V82.53","scheme":"https","certificate_verification_required":True,
       "minimum_tls_version":"1.2","plaintext_http_allowed":False}
    d["tls_sha256"]=hj(d);return d

def provider_compatibility(contract,schemas):
    d={"stage":"V82.54","provider":"ALPACA_COMPATIBLE",
       "endpoint_contract_valid":validate_endpoint_contract(contract)["status"]=="PASS",
       "schema_contract_valid":schemas["schema_count"]==6,
       "read_only_compatible":True,"write_compatible":False}
    d["compatibility_sha256"]=hj(d);return d

def connection_health(heartbeat,validations):
    failed=[x["stage"] for x in validations if x["status"]!="PASS"]
    d={"stage":"V82.55","status":"PASS" if heartbeat["healthy"] and not failed else "FAIL",
       "heartbeat_healthy":heartbeat["healthy"],"validation_count":len(validations),
       "failed_validation_stages":failed,"network_requests_executed":0,
       "broker_connected":False}
    d["health_sha256"]=hj(d);return d

def build_audit(config,contract,credential,timeout,retry,rate,tls,compatibility,health):
    checks={"config_safe":config.mode=="OFFLINE_CONNECTION_VALIDATION",
      "write_endpoints_zero":contract["write_endpoint_count"]==0,
      "credentials_zero":credential["credentials_used"]==0,
      "timeout_network_blocked":timeout["network_execution_authorized"] is False,
      "retry_network_blocked":retry["network_execution_authorized"] is False,
      "rate_network_zero":rate["network_requests_executed"]==0,
      "tls_required":tls["certificate_verification_required"],
      "read_only_compatible":compatibility["read_only_compatible"],
      "write_not_compatible":compatibility["write_compatible"] is False,
      "health_pass":health["status"]=="PASS",
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V82.56","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def _result(stage,checks):
    failed=[k for k,v in checks.items() if not v]
    d={"stage":stage,"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["validation_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="broker-connection-validation-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V82.57","status":"PASS","package_id":pid,"document_count":len(docs),
      "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"broker_connection_validation_master_ledger_v82_57.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"broker_connection_validation_master_ledger_v82_57.json";b=lp.read_bytes()
    d={"stage":"V82.58","status":"PASS","package_id":ledger["package_id"],
      "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"broker_connection_validation_manifest_v82_58.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"broker_connection_validation_master_ledger_v82_57.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_read_only_certificate(root/"release/v82_40/output/broker_read_only_foundation_certificate_v82_40.json")
    contract=endpoint_contract();endpoint_v=validate_endpoint_contract(contract)
    credential=credential_shape_fixture();credential_v=validate_credential_shape(credential)
    timeout=timeout_policy(c);retry=retry_policy(c);rate=rate_limit_policy(c);heartbeat=heartbeat_fixture()
    schemas=response_schema_contract();schema_v=validate_response_schemas(schemas,sample_responses())
    errors=error_classification();error_v=validate_error_classification(errors);tls=tls_contract()
    compatibility=provider_compatibility(contract,schemas)
    validations=[endpoint_v,credential_v,schema_v,error_v]
    health=connection_health(heartbeat,validations)
    audit=build_audit(c,contract,credential,timeout,retry,rate,tls,compatibility,health)
    docs={"endpoint_contract":contract,"endpoint_validation":endpoint_v,"credential_shape":credential,
      "credential_validation":credential_v,"timeout_policy":timeout,"retry_policy":retry,"rate_limit_policy":rate,
      "heartbeat":heartbeat,"response_schemas":schemas,"schema_validation":schema_v,
      "error_classification":errors,"error_validation":error_v,"tls_contract":tls,
      "provider_compatibility":compatibility,"connection_health":health,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"provider":c.provider,"endpoint_count":contract["endpoint_count"],
      "write_endpoint_count":contract["write_endpoint_count"],"schema_count":schemas["schema_count"],
      "error_code_count":errors["error_code_count"],"heartbeat_healthy":heartbeat["healthy"],
      "connection_health_status":health["status"],"read_only_compatible":compatibility["read_only_compatible"],
      "write_compatible":compatibility["write_compatible"],"audit_status":audit["status"],
      "source_read_only_complete":source["broker_read_only_foundation_complete"]}
    return {"stage":"V82.59","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v82_40_certificate_present":(root/"release/v82_40/output/broker_read_only_foundation_certificate_v82_40.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","endpoint_count_six":s["endpoint_count"]==6,
      "write_endpoints_zero":s["write_endpoint_count"]==0,"schema_count_six":s["schema_count"]==6,
      "heartbeat_healthy":s["heartbeat_healthy"],"connection_health_pass":s["connection_health_status"]=="PASS",
      "read_only_compatible":s["read_only_compatible"],"write_not_compatible":s["write_compatible"] is False,
      "audit_pass":s["audit_status"]=="PASS","manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V82.60","status":status,"scope":"OFFLINE_BROKER_CONNECTION_VALIDATION_FOUNDATION",
      "stages_completed":[f"V82.{i:02d}" for i in range(41,61)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"broker_connection_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "broker_connection_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_trading_authorized":False,"live_trading_authorized":False,
      "broker_connection_validation_complete":status=="PASS",
      "next_phase":"V82_61_DRY_RUN_BROKER_VALIDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"broker_connection_validation_certificate_v82_60.json",cert)
    wj(out/"broker_connection_validation_verify_v82_60.json",{"stage":"V82.60","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
