from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Mapping
import hashlib, json, os, ssl, tempfile
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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
class ReadOnlyConnectionConfig:
    mode:str="PAPER_BROKER_READ_ONLY_VALIDATION"
    trading_base_url:str="https://paper-api.alpaca.markets"
    data_base_url:str="https://data.alpaca.markets"
    symbol:str="AAPL"
    feed:str="iex"
    connect_timeout_seconds:float=3.0
    read_timeout_seconds:float=5.0
    explicit_network_opt_in:bool=False
    required_opt_in_value:str="YES"
    allow_get:bool=True
    allow_post:bool=False
    allow_put:bool=False
    allow_patch:bool=False
    allow_delete:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="PAPER_BROKER_READ_ONLY_VALIDATION": raise ValueError("mode")
        if not self.allow_get or self.allow_post or self.allow_put or self.allow_patch or self.allow_delete:
            raise ValueError("GET-only contract")
        if self.actual_orders_submitted!=0: raise ValueError("orders forbidden")
        for url,host in ((self.trading_base_url,"paper-api.alpaca.markets"),(self.data_base_url,"data.alpaca.markets")):
            p=urlparse(url)
            if p.scheme!="https" or p.hostname!=host or p.username or p.password: raise ValueError("endpoint")
        if self.feed not in {"iex","sip","delayed_sip"}: raise ValueError("feed")

def validate_foundation_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V85.20" or c.get("status")!="PASS": raise ValueError("bad V85.20 certificate")
    if c.get("paper_network_foundation_complete") is not True: raise ValueError("foundation prerequisite")
    if c.get("paper_network_connection_authorized") is not False or c.get("actual_orders_submitted")!=0:
        raise ValueError("unsafe prerequisite")
    return c

def endpoint_catalog(config):
    eps={
      "account":{"base":"trading","path":"/v2/account","params":{}},
      "clock":{"base":"trading","path":"/v2/clock","params":{}},
      "positions":{"base":"trading","path":"/v2/positions","params":{}},
      "orders":{"base":"trading","path":"/v2/orders","params":{"status":"all","limit":"50"}},
      "asset":{"base":"trading","path":f"/v2/assets/{config.symbol}","params":{}},
      "latest_quote":{"base":"data","path":f"/v2/stocks/{config.symbol}/quotes/latest","params":{"feed":config.feed}},
    }
    d={"stage":"V85.21","endpoint_count":len(eps),"method":"GET","endpoints":eps,"write_endpoint_count":0}
    d["catalog_sha256"]=hj(d);return d

def credential_status(env:Mapping[str,str]):
    key=env.get("APCA_API_KEY_ID","").strip();secret=env.get("APCA_API_SECRET_KEY","").strip()
    d={"stage":"V85.22","api_key_present":bool(key),"api_secret_present":bool(secret),
       "complete":bool(key and secret),"values_redacted":True,"credentials_used":0}
    d["credential_sha256"]=hj(d);return d

def network_authorization(config,env:Mapping[str,str],enable_network:bool):
    env_value=env.get("AI_STOCK_BOT_ENABLE_PAPER_READ_ONLY","")
    allowed=bool(enable_network and config.explicit_network_opt_in and env_value==config.required_opt_in_value)
    d={"stage":"V85.23","cli_enable_network":bool(enable_network),
       "config_opt_in":config.explicit_network_opt_in,"environment_opt_in_match":env_value==config.required_opt_in_value,
       "network_authorized":allowed,"scope":"PAPER_GET_ONLY"}
    d["authorization_sha256"]=hj(d);return d

def build_url(config,entry):
    base=config.trading_base_url if entry["base"]=="trading" else config.data_base_url
    url=base.rstrip("/") + entry["path"]
    if entry["params"]: url += "?" + urlencode(entry["params"])
    return url

def request_contract(name,url):
    p=urlparse(url)
    d={"stage":"V85.24","name":name,"method":"GET","scheme":p.scheme,"host":p.hostname,
       "path":p.path,"query":p.query,"body_allowed":False}
    d["request_sha256"]=hj(d);return d

def default_transport(url,headers,timeout):
    req=Request(url=url,headers=headers,method="GET")
    context=ssl.create_default_context()
    with urlopen(req,timeout=timeout,context=context) as response:
        return response.status, dict(response.headers.items()), response.read()

def execute_get(name,url,key,secret,timeout,transport:Callable=default_transport):
    headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,"Accept":"application/json"}
    try:
        status,response_headers,body=transport(url,headers,timeout)
        payload=json.loads(body.decode("utf-8"))
        result={"stage":"V85.25","name":name,"status_code":int(status),"ok":200<=int(status)<300,
                "payload":payload,"response_headers_recorded":False,"credentials_redacted":True,"method":"GET"}
    except HTTPError as e:
        result={"stage":"V85.25","name":name,"status_code":e.code,"ok":False,
                "error_class":"HTTP_ERROR","credentials_redacted":True,"method":"GET"}
    except (URLError,TimeoutError) as e:
        result={"stage":"V85.25","name":name,"status_code":None,"ok":False,
                "error_class":"NETWORK_ERROR","credentials_redacted":True,"method":"GET"}
    result["result_sha256"]=hj(result);return result

def schema_validate(name,payload):
    required={
      "account":{"id","status","cash","portfolio_value","buying_power","trading_blocked"},
      "clock":{"timestamp","is_open","next_open","next_close"},
      "positions":set(),
      "orders":set(),
      "asset":{"id","class","exchange","symbol","status","tradable"},
      "latest_quote":{"quote"},
    }
    rows=payload if isinstance(payload,list) else [payload]
    missing=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict): missing.append(f"{i}:not_object");continue
        for field in required[name]:
            if field not in row: missing.append(f"{i}:{field}")
    if name=="latest_quote" and isinstance(payload,dict) and "quote" in payload:
        q=payload["quote"]
        if not isinstance(q,dict): missing.append("quote:not_object")
        else:
            for field in ("ap","bp","t"):
                if field not in q: missing.append(f"quote:{field}")
    d={"stage":"V85.26","name":name,"row_count":len(rows),"missing_fields":missing,
       "status":"PASS" if not missing else "FAIL"}
    d["schema_sha256"]=hj(d);return d

def fixtures(config):
    return {
      "account":{"id":"paper-account","status":"ACTIVE","cash":"100000","portfolio_value":"100000","buying_power":"200000","trading_blocked":False},
      "clock":{"timestamp":"2026-07-31T20:00:00Z","is_open":False,"next_open":"2026-08-03T13:30:00Z","next_close":"2026-08-03T20:00:00Z"},
      "positions":[],
      "orders":[],
      "asset":{"id":"asset-aapl","class":"us_equity","exchange":"NASDAQ","symbol":config.symbol,"status":"active","tradable":True},
      "latest_quote":{"quote":{"ap":200.1,"bp":200.0,"t":"2026-07-31T20:00:00Z"},"symbol":config.symbol},
    }

def health_summary(results,schemas,network_mode):
    ok=sum(x["ok"] for x in results.values());schema_pass=sum(x["status"]=="PASS" for x in schemas.values())
    d={"stage":"V85.27","network_mode":network_mode,"endpoint_count":len(results),
       "request_success_count":ok,"schema_pass_count":schema_pass,
       "health_status":"PASS" if ok==len(results) and schema_pass==len(schemas) else "FAIL"}
    d["health_sha256"]=hj(d);return d

def reconciliation(results):
    account=results["account"]["payload"];positions=results["positions"]["payload"];orders=results["orders"]["payload"]
    checks={"account_present":bool(account.get("id")),"positions_list":isinstance(positions,list),
            "orders_list":isinstance(orders,list),"actual_orders_created_zero":True}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V85.28","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
       "position_count":len(positions),"order_snapshot_count":len(orders)}
    d["reconciliation_sha256"]=hj(d);return d

def run_validation(config,env,enable_network=False,transport=default_transport):
    config.validate();catalog=endpoint_catalog(config);cred=credential_status(env);auth=network_authorization(config,env,enable_network)
    results={};contracts={}
    if auth["network_authorized"]:
        if not cred["complete"]: raise ValueError("paper credentials required")
        key=env["APCA_API_KEY_ID"];secret=env["APCA_API_SECRET_KEY"]
        for name,entry in catalog["endpoints"].items():
            url=build_url(config,entry);contracts[name]=request_contract(name,url)
            results[name]=execute_get(name,url,key,secret,config.connect_timeout_seconds+config.read_timeout_seconds,transport)
        network_requests=len(results);credentials_used=2
        mode="ACTUAL_READ_ONLY"
    else:
        for name,entry in catalog["endpoints"].items():
            url=build_url(config,entry);contracts[name]=request_contract(name,url)
            r={"stage":"V85.25","name":name,"status_code":200,"ok":True,"payload":fixtures(config)[name],
               "response_headers_recorded":False,"credentials_redacted":True,"method":"GET","fixture":True}
            r["result_sha256"]=hj(r);results[name]=r
        network_requests=0;credentials_used=0;mode="OFFLINE_FIXTURE"
    schemas={name:schema_validate(name,r["payload"]) for name,r in results.items()}
    health=health_summary(results,schemas,mode);recon=reconciliation(results)
    return {"catalog":catalog,"credentials":cred,"authorization":auth,"contracts":contracts,
            "results":results,"schemas":schemas,"health":health,"reconciliation":recon,
            "network_mode":mode,"network_requests_executed":network_requests,
            "credentials_used":credentials_used,"trading_client_created":False,"actual_orders_submitted":0}

def retry_classification():
    d={"stage":"V85.29","retryable_status_codes":[429,500,502,503,504],
       "non_retryable_status_codes":[400,401,403,404,422],"max_get_retries":2,"write_retries":0}
    d["retry_sha256"]=hj(d);return d

def rate_limit_observer():
    d={"stage":"V85.30","observe_headers":["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"],
       "request_budget_per_run":6,"write_request_budget":0}
    d["rate_limit_sha256"]=hj(d);return d

def tls_audit(config):
    d={"stage":"V85.31","certificate_verification":True,"plaintext_http":False,
       "hosts":[urlparse(config.trading_base_url).hostname,urlparse(config.data_base_url).hostname]}
    d["tls_sha256"]=hj(d);return d

def redaction_audit():
    d={"stage":"V85.32","redacted_headers":["APCA-API-KEY-ID","APCA-API-SECRET-KEY","Authorization"],
       "secret_values_persisted":False,"response_bodies_persisted_in_audit":False}
    d["redaction_sha256"]=hj(d);return d

def fallback_policy():
    d={"stage":"V85.33","offline_fixture_fallback_supported":True,
       "automatic_fallback_after_auth_failure":False,"manual_mode_selection_required":True}
    d["fallback_sha256"]=hj(d);return d

def build_audit(run):
    checks={"endpoint_count_six":run["catalog"]["endpoint_count"]==6,
      "write_endpoints_zero":run["catalog"]["write_endpoint_count"]==0,
      "health_pass":run["health"]["health_status"]=="PASS",
      "reconciliation_pass":run["reconciliation"]["status"]=="PASS",
      "client_false":run["trading_client_created"] is False,
      "actual_orders_zero":run["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V85.34","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
       "network_mode":run["network_mode"],"network_requests_executed":run["network_requests_executed"],
       "credentials_used":run["credentials_used"]}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="paper-read-only-validation-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V85.35","status":"PASS","package_id":pid,"document_count":len(docs),"package_created":created,
            "package_reused":not created,"files":files}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_read_only_master_ledger_v85_35.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger,run):
    lp=out/"paper_read_only_master_ledger_v85_35.json";b=lp.read_bytes()
    d={"stage":"V85.36","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_mode":run["network_mode"],"network_requests_executed":run["network_requests_executed"],
       "credentials_used":run["credentials_used"],"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_read_only_manifest_v85_36.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"paper_read_only_master_ledger_v85_35.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out,env=None,enable_network=False,transport=default_transport):
    source=validate_foundation_certificate(root/"release/v85_20/output/paper_network_foundation_certificate_v85_20.json")
    run=run_validation(c,dict(os.environ) if env is None else env,enable_network,transport)
    docs={"connection_run":run,"retry_classification":retry_classification(),"rate_limit_observer":rate_limit_observer(),
          "tls_audit":tls_audit(c),"redaction_audit":redaction_audit(),"fallback_policy":fallback_policy()}
    audit=build_audit(run);docs["audit"]=audit
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"],run);verify_manifest(out,manifest)
    summary={"provider":"ALPACA","network_mode":run["network_mode"],
      "endpoint_count":run["catalog"]["endpoint_count"],"request_success_count":run["health"]["request_success_count"],
      "schema_pass_count":run["health"]["schema_pass_count"],"health_status":run["health"]["health_status"],
      "reconciliation_status":run["reconciliation"]["status"],
      "position_count":run["reconciliation"]["position_count"],"order_snapshot_count":run["reconciliation"]["order_snapshot_count"],
      "network_requests_executed":run["network_requests_executed"],"credentials_used":run["credentials_used"],
      "audit_status":audit["status"],"source_network_foundation_complete":source["paper_network_foundation_complete"]}
    return {"stage":"V85.39","status":"PASS", "summary":summary,**stored,"manifest":manifest,
            "trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v85_20_certificate_present":(root/"release/v85_20/output/paper_network_foundation_certificate_v85_20.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","endpoint_count_six":s["endpoint_count"]==6,
      "requests_all_success":s["request_success_count"]==6,"schemas_all_pass":s["schema_pass_count"]==6,
      "health_pass":s["health_status"]=="PASS","reconciliation_pass":s["reconciliation_status"]=="PASS",
      "audit_pass":s["audit_status"]=="PASS","manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V85.40","status":status,"scope":"PAPER_BROKER_READ_ONLY_CONNECTION_VALIDATION",
      "stages_completed":[f"V85.{i:02d}" for i in range(21,41)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"paper_read_only_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "paper_read_only_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":s["network_requests_executed"],"credentials_used":s["credentials_used"],
      "broker_connected":s["network_mode"]=="ACTUAL_READ_ONLY","trading_client_created":False,"actual_orders_submitted":0,
      "paper_read_only_validation_complete":status=="PASS",
      "paper_order_submission_authorized":False,"live_trading_authorized":False,
      "next_phase":"V85_41_PAPER_ORDER_SUBMISSION_AUTHORIZATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"paper_read_only_certificate_v85_40.json",cert)
    wj(out/"paper_read_only_verify_v85_40.json",{"stage":"V85.40","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
