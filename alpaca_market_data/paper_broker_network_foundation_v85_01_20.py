from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping
import hashlib, json, os, tempfile
from urllib.parse import urlparse

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
class PaperBrokerNetworkFoundationConfig:
    mode:str="PAPER_BROKER_NETWORK_FOUNDATION"
    provider:str="ALPACA"
    base_url:str="https://paper-api.alpaca.markets"
    data_url:str="https://data.alpaca.markets"
    explicit_network_opt_in:bool=False
    read_only:bool=True
    allow_account_read:bool=True
    allow_positions_read:bool=True
    allow_orders_read:bool=True
    allow_clock_read:bool=True
    allow_assets_read:bool=True
    allow_market_data_read:bool=True
    allow_order_submission:bool=False
    allow_order_cancel:bool=False
    allow_order_replace:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="PAPER_BROKER_NETWORK_FOUNDATION": raise ValueError("mode")
        if self.provider!="ALPACA": raise ValueError("provider")
        if not self.read_only: raise ValueError("read only required")
        if self.allow_order_submission or self.allow_order_cancel or self.allow_order_replace:
            raise ValueError("write capability forbidden")
        if self.actual_orders_submitted!=0: raise ValueError("orders forbidden")
        validate_endpoint(self.base_url, "paper-api.alpaca.markets")
        validate_endpoint(self.data_url, "data.alpaca.markets")

def validate_endpoint(url:str, expected_host:str)->dict[str,Any]:
    p=urlparse(url)
    allowed=p.scheme=="https" and p.hostname==expected_host and not p.username and not p.password
    d={"stage":"V85.01","url":url,"scheme":p.scheme,"host":p.hostname,"expected_host":expected_host,"allowed":allowed}
    d["endpoint_sha256"]=hj(d)
    if not allowed: raise ValueError("endpoint")
    return d

def validate_live_framework_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V85.00" or c.get("status")!="PASS": raise ValueError("bad V85.00 certificate")
    if c.get("live_broker_framework_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("framework prerequisite")
    if c.get("live_trading_authorized") is not False: raise ValueError("unsafe prerequisite")
    return c

def credential_contract():
    d={"stage":"V85.02","required_names":["APCA_API_KEY_ID","APCA_API_SECRET_KEY"],
       "optional_names":["APCA_API_BASE_URL"],"secret_values_stored":False,
       "environment_read_performed":False}
    d["credential_contract_sha256"]=hj(d);return d

def inspect_credentials(values:Mapping[str,str])->dict[str,Any]:
    key=bool(values.get("APCA_API_KEY_ID","").strip())
    secret=bool(values.get("APCA_API_SECRET_KEY","").strip())
    d={"stage":"V85.03","api_key_present":key,"api_secret_present":secret,
       "complete":key and secret,"values_redacted":True,"secret_values_stored":False}
    d["credential_status_sha256"]=hj(d);return d

def capability_registry(config):
    caps={
      "account_read":config.allow_account_read,
      "positions_read":config.allow_positions_read,
      "orders_read":config.allow_orders_read,
      "clock_read":config.allow_clock_read,
      "assets_read":config.allow_assets_read,
      "market_data_read":config.allow_market_data_read,
      "order_submit":config.allow_order_submission,
      "order_cancel":config.allow_order_cancel,
      "order_replace":config.allow_order_replace,
    }
    d={"stage":"V85.04","capabilities":caps,
       "read_capability_count":sum(v for k,v in caps.items() if k.endswith("_read")),
       "write_capability_count":sum(v for k,v in caps.items() if k.startswith("order_") and not k.endswith("_read"))}
    d["registry_sha256"]=hj(d);return d

def endpoint_catalog(config):
    endpoints={
      "account":{"method":"GET","path":"/v2/account","write":False},
      "positions":{"method":"GET","path":"/v2/positions","write":False},
      "orders":{"method":"GET","path":"/v2/orders","write":False},
      "clock":{"method":"GET","path":"/v2/clock","write":False},
      "assets":{"method":"GET","path":"/v2/assets","write":False},
      "latest_quotes":{"method":"GET","path":"/v2/stocks/quotes/latest","write":False},
    }
    d={"stage":"V85.05","endpoint_count":len(endpoints),"endpoints":endpoints,
       "write_endpoint_count":sum(x["write"] for x in endpoints.values())}
    d["catalog_sha256"]=hj(d);return d

def network_opt_in(config,requested:bool)->dict[str,Any]:
    allowed=config.explicit_network_opt_in and requested
    d={"stage":"V85.06","configured_opt_in":config.explicit_network_opt_in,
       "requested":requested,"network_allowed":allowed}
    d["opt_in_sha256"]=hj(d);return d

def request_plan(endpoint_name,catalog,credential_status,opt_in):
    if endpoint_name not in catalog["endpoints"]: raise ValueError("unknown endpoint")
    ep=catalog["endpoints"][endpoint_name]
    checks={"read_only":not ep["write"],"credentials_complete":credential_status["complete"],
            "network_opt_in":opt_in["network_allowed"]}
    ready=all(checks.values())
    d={"stage":"V85.07","endpoint_name":endpoint_name,"method":ep["method"],"path":ep["path"],
       "checks":checks,"ready_for_network_probe":ready,"order_submission_possible":False}
    d["request_plan_sha256"]=hj(d);return d

def response_schema_catalog():
    schemas={
      "account":["id","status","currency","cash","portfolio_value","buying_power","trading_blocked"],
      "positions":["symbol","qty","market_value","avg_entry_price","unrealized_pl"],
      "orders":["id","client_order_id","symbol","side","type","status","qty","filled_qty"],
      "clock":["timestamp","is_open","next_open","next_close"],
      "assets":["id","class","exchange","symbol","status","tradable"],
      "latest_quotes":["symbol","ask_price","bid_price","timestamp"],
    }
    d={"stage":"V85.08","schema_count":len(schemas),"schemas":schemas}
    d["schema_catalog_sha256"]=hj(d);return d

def validate_response(name,payload):
    schemas=response_schema_catalog()["schemas"]
    if name not in schemas: raise ValueError("schema")
    rows=payload if isinstance(payload,list) else [payload]
    missing=[]
    for i,row in enumerate(rows):
        for field in schemas[name]:
            if field not in row: missing.append(f"{i}:{field}")
    d={"stage":"V85.09","schema":name,"row_count":len(rows),"missing_fields":missing,
       "status":"PASS" if not missing else "FAIL"}
    d["response_validation_sha256"]=hj(d);return d

def timeout_policy():
    d={"stage":"V85.10","connect_timeout_seconds":3,"read_timeout_seconds":5,
       "total_timeout_seconds":8,"infinite_timeout_allowed":False}
    d["timeout_sha256"]=hj(d);return d

def retry_policy():
    d={"stage":"V85.11","retry_limit":2,"retryable_status_codes":[429,500,502,503,504],
       "non_retryable_status_codes":[400,401,403,404,422],"write_retry_enabled":False}
    d["retry_sha256"]=hj(d);return d

def rate_limit_policy():
    d={"stage":"V85.12","max_requests_per_minute":120,"burst_limit":10,
       "write_requests_per_minute":0,"backoff_required":True}
    d["rate_limit_sha256"]=hj(d);return d

def tls_policy(config):
    hosts=[urlparse(config.base_url).hostname,urlparse(config.data_url).hostname]
    d={"stage":"V85.13","https_required":True,"certificate_verification_required":True,
       "allowed_hosts":hosts,"plaintext_http_allowed":False}
    d["tls_sha256"]=hj(d);return d

def redaction_policy():
    d={"stage":"V85.14","redacted_headers":["APCA-API-KEY-ID","APCA-API-SECRET-KEY","Authorization"],
       "log_request_bodies":False,"log_response_bodies":False,"secret_hashing_allowed":False}
    d["redaction_sha256"]=hj(d);return d

def offline_fixtures():
    d={"stage":"V85.15","fixtures":{
      "account":{"id":"acct-paper","status":"ACTIVE","currency":"USD","cash":"100000","portfolio_value":"100000","buying_power":"200000","trading_blocked":False},
      "positions":[],
      "orders":[],
      "clock":{"timestamp":"2026-07-31T20:00:00Z","is_open":False,"next_open":"2026-08-03T13:30:00Z","next_close":"2026-08-03T20:00:00Z"},
      "assets":[{"id":"asset-aapl","class":"us_equity","exchange":"NASDAQ","symbol":"AAPL","status":"active","tradable":True}],
      "latest_quotes":[{"symbol":"AAPL","ask_price":200.1,"bid_price":200.0,"timestamp":"2026-07-31T20:00:00Z"}],
    }}
    d["fixtures_sha256"]=hj(d);return d

def validation_scenarios(config):
    fixtures=offline_fixtures()["fixtures"]
    results={name:validate_response(name,payload) for name,payload in fixtures.items()}
    bad=dict(fixtures["account"]);bad.pop("cash")
    bad_result=validate_response("account",bad)
    cred_good=inspect_credentials({"APCA_API_KEY_ID":"key","APCA_API_SECRET_KEY":"secret"})
    cred_bad=inspect_credentials({})
    opt_in=network_opt_in(config,True)
    catalog=endpoint_catalog(config)
    plans={name:request_plan(name,catalog,cred_good,opt_in) for name in catalog["endpoints"]}
    d={"stage":"V85.16","status":"PASS",
       "fixture_validation_pass_count":sum(x["status"]=="PASS" for x in results.values()),
       "fixture_validation_count":len(results),
       "bad_fixture_rejected":bad_result["status"]=="FAIL",
       "credential_complete_detected":cred_good["complete"],
       "credential_missing_detected":not cred_bad["complete"],
       "network_probe_ready_count":sum(x["ready_for_network_probe"] for x in plans.values()),
       "actual_network_requests":0,"actual_orders_submitted":0}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,registry,catalog,scenarios):
    checks={"read_capabilities_positive":registry["read_capability_count"]>0,
      "write_capabilities_zero":registry["write_capability_count"]==0,
      "endpoint_count_six":catalog["endpoint_count"]==6,
      "write_endpoints_zero":catalog["write_endpoint_count"]==0,
      "fixture_validation_complete":scenarios["fixture_validation_pass_count"]==scenarios["fixture_validation_count"],
      "bad_fixture_rejected":scenarios["bad_fixture_rejected"],
      "credential_complete_detected":scenarios["credential_complete_detected"],
      "credential_missing_detected":scenarios["credential_missing_detected"],
      "actual_network_zero":scenarios["actual_network_requests"]==0,
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V85.17","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="paper-network-foundation-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V85.18","status":"PASS","package_id":pid,"document_count":len(docs),"package_created":created,
            "package_reused":not created,"files":files,"actual_orders_submitted":0,"network_requests_executed":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_network_foundation_master_ledger_v85_18.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"paper_network_foundation_master_ledger_v85_18.json";b=lp.read_bytes()
    d={"stage":"V85.19","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_network_foundation_manifest_v85_19.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"paper_network_foundation_master_ledger_v85_18.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_live_framework_certificate(root/"release/v85_00/output/live_broker_final_certificate_v85_00.json")
    docs={"credential_contract":credential_contract(),"capability_registry":capability_registry(c),
      "endpoint_catalog":endpoint_catalog(c),"response_schemas":response_schema_catalog(),
      "timeout_policy":timeout_policy(),"retry_policy":retry_policy(),"rate_limit_policy":rate_limit_policy(),
      "tls_policy":tls_policy(c),"redaction_policy":redaction_policy(),"offline_fixtures":offline_fixtures()}
    scenarios=validation_scenarios(c);docs["validation_scenarios"]=scenarios
    audit=build_audit(c,docs["capability_registry"],docs["endpoint_catalog"],scenarios);docs["audit"]=audit
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"provider":c.provider,"read_capability_count":docs["capability_registry"]["read_capability_count"],
      "write_capability_count":docs["capability_registry"]["write_capability_count"],
      "endpoint_count":docs["endpoint_catalog"]["endpoint_count"],
      "write_endpoint_count":docs["endpoint_catalog"]["write_endpoint_count"],
      "schema_count":docs["response_schemas"]["schema_count"],
      "credential_contract_ready":True,"network_opt_in_default":c.explicit_network_opt_in,
      "actual_network_requests":0,"audit_status":audit["status"],
      "source_live_framework_complete":source["live_broker_framework_complete"]}
    return {"stage":"V85.20","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v85_00_certificate_present":(root/"release/v85_00/output/live_broker_final_certificate_v85_00.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","read_capabilities_positive":s["read_capability_count"]>0,
      "write_capabilities_zero":s["write_capability_count"]==0,"endpoint_count_six":s["endpoint_count"]==6,
      "write_endpoints_zero":s["write_endpoint_count"]==0,"schema_count_six":s["schema_count"]==6,
      "network_opt_in_default_false":s["network_opt_in_default"] is False,
      "actual_network_zero":s["actual_network_requests"]==0,"audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V85.20","status":status,"scope":"PAPER_BROKER_NETWORK_CONNECTION_FOUNDATION",
      "stages_completed":[f"V85.{i:02d}" for i in range(1,21)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"paper_network_foundation_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "paper_network_foundation_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_network_connection_authorized":False,"paper_order_submission_authorized":False,
      "live_trading_authorized":False,"paper_network_foundation_complete":status=="PASS",
      "next_phase":"V85_21_PAPER_BROKER_READ_ONLY_CONNECTION_VALIDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"paper_network_foundation_certificate_v85_20.json",cert)
    wj(out/"paper_network_foundation_verify_v85_20.json",{"stage":"V85.20","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
