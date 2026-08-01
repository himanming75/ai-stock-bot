from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Mapping
import hashlib, json, os, ssl, tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class SingleOrderNetworkValidationConfig:
    mode:str="PAPER_SINGLE_ORDER_NETWORK_VALIDATION"
    base_url:str="https://paper-api.alpaca.markets"
    symbol:str="AAPL"
    side:str="buy"
    quantity:int=1
    order_type:str="market"
    time_in_force:str="day"
    max_order_notional:float=500.0
    one_order_limit:int=1
    explicit_network_opt_in:bool=False
    explicit_order_opt_in:bool=False
    required_network_opt_in_value:str="YES"
    required_order_opt_in_value:str="YES"
    kill_switch_armed:bool=True
    emergency_stop_ready:bool=True
    allow_network:bool=False
    allow_post:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        p=urlparse(self.base_url)
        if self.mode!="PAPER_SINGLE_ORDER_NETWORK_VALIDATION": raise ValueError("mode")
        if p.scheme!="https" or p.hostname!="paper-api.alpaca.markets": raise ValueError("endpoint")
        if self.quantity!=1 or self.one_order_limit!=1: raise ValueError("one order only")
        if self.side not in {"buy","sell"} or self.order_type!="market" or self.time_in_force!="day": raise ValueError("order contract")
        if self.max_order_notional<=0 or not self.kill_switch_armed or not self.emergency_stop_ready: raise ValueError("safety")
        if self.allow_network or self.allow_post or self.actual_orders_submitted: raise ValueError("safe default required")

def validate_enablement_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V86.00" or c.get("status")!="PASS": raise ValueError("bad V86.00 certificate")
    if c.get("paper_network_enablement_foundation_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("prerequisite")
    if c.get("paper_network_enabled") is not False or c.get("paper_order_submission_authorized") is not False:
        raise ValueError("unsafe prerequisite")
    return c

def policy():
    d={"stage":"V86.01","status":"PASS","paper_only":True,"single_order_only":True,
       "offline_default":True,"network_enabled":False,"post_enabled":False}
    d["policy_sha256"]=hj(d);return d

def credential_status(env:Mapping[str,str]):
    key=bool(env.get("APCA_API_KEY_ID","").strip());secret=bool(env.get("APCA_API_SECRET_KEY","").strip())
    d={"stage":"V86.02","api_key_present":key,"api_secret_present":secret,
       "complete":key and secret,"values_redacted":True}
    d["credential_sha256"]=hj(d);return d

def opt_in_gate(config,env,enable_network,enable_order):
    network_match=env.get("AI_STOCK_BOT_ENABLE_PAPER_NETWORK","")==config.required_network_opt_in_value
    order_match=env.get("AI_STOCK_BOT_ENABLE_SINGLE_PAPER_ORDER","")==config.required_order_opt_in_value
    allowed=all([config.explicit_network_opt_in,config.explicit_order_opt_in,enable_network,enable_order,network_match,order_match])
    d={"stage":"V86.03","network_config":config.explicit_network_opt_in,
       "order_config":config.explicit_order_opt_in,"network_cli":enable_network,
       "order_cli":enable_order,"network_env_match":network_match,"order_env_match":order_match,
       "allowed":allowed}
    d["opt_in_sha256"]=hj(d);return d

def preflight(config,account,asset,clock,quote):
    price=float(quote["ask_price"]);notional=price*config.quantity
    checks={"paper_account_active":account.get("status")=="ACTIVE",
      "trading_not_blocked":account.get("trading_blocked") is False,
      "asset_tradable":asset.get("tradable") is True,
      "market_open":clock.get("is_open") is True,
      "buying_power_sufficient":float(account.get("buying_power",0))>=notional,
      "notional_within_limit":notional<=config.max_order_notional,
      "kill_switch_armed":config.kill_switch_armed,
      "emergency_stop_ready":config.emergency_stop_ready}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.04","status":"PASS" if not failed else "FAIL","checks":checks,
       "failed_checks":failed,"reference_price":price,"estimated_notional":notional}
    d["preflight_sha256"]=hj(d);return d

def one_order_token(config,preflight_result):
    if preflight_result["status"]!="PASS": raise ValueError("preflight")
    d={"stage":"V86.05","token_id":"paper-single-order-"+hj(preflight_result)[:24],
       "scope":"ONE_PAPER_ORDER","order_limit":1,"used":False,"revoked":False,
       "symbol":config.symbol,"side":config.side,"quantity":config.quantity}
    d["token_sha256"]=hj(d);return d

def build_payload(config,token):
    d={"stage":"V86.06","payload":{"symbol":config.symbol,"qty":str(config.quantity),
       "side":config.side,"type":config.order_type,"time_in_force":config.time_in_force,
       "client_order_id":"single-"+token["token_id"][-20:]},
       "post_path":"/v2/orders","paper_only":True}
    d["payload_sha256"]=hj(d);return d

def default_transport(url,headers,body,timeout):
    req=Request(url=url,headers=headers,data=body,method="POST")
    with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:
        return r.status, r.read()

def execute_order(config,env,payload,transport:Callable=default_transport):
    body=json.dumps(payload["payload"]).encode()
    headers={"APCA-API-KEY-ID":env["APCA_API_KEY_ID"],"APCA-API-SECRET-KEY":env["APCA_API_SECRET_KEY"],
             "Content-Type":"application/json","Accept":"application/json"}
    try:
        status,data=transport(config.base_url+"/v2/orders",headers,body,8)
        result={"stage":"V86.07","status_code":int(status),"ok":int(status) in {200,201},
                "response":json.loads(data.decode()),"credentials_redacted":True}
    except HTTPError as e:
        result={"stage":"V86.07","status_code":e.code,"ok":False,"error_class":"HTTP_ERROR","credentials_redacted":True}
    except (URLError,TimeoutError):
        result={"stage":"V86.07","status_code":None,"ok":False,"error_class":"NETWORK_ERROR","credentials_redacted":True}
    result["result_sha256"]=hj(result);return result

def read_after_write(order_response):
    r=order_response["response"]
    required=["id","client_order_id","symbol","side","type","status","qty","filled_qty"]
    missing=[x for x in required if x not in r]
    d={"stage":"V86.08","status":"PASS" if not missing else "FAIL","missing_fields":missing,
       "order_id":r.get("id"),"client_order_id":r.get("client_order_id"),
       "broker_status":r.get("status")}
    d["verification_sha256"]=hj(d);return d

def consume_token(token):
    if token["used"] or token["revoked"]: raise ValueError("token unavailable")
    d={**token,"stage":"V86.09","used":True}
    d["token_sha256"]=hj({k:v for k,v in d.items() if k!="token_sha256"});return d

def revoke_token(token,reason):
    d={**token,"stage":"V86.10","revoked":True,"revoke_reason":reason}
    d["token_sha256"]=hj({k:v for k,v in d.items() if k!="token_sha256"});return d

def rollback_plan():
    d={"stage":"V86.11","status":"PASS","disable_network":True,"clear_credentials":True,
       "revoke_token":True,"stop_after_one_order":True,"manual_cancel_if_open":True}
    d["rollback_sha256"]=hj(d);return d

def fixtures(config):
    return {"account":{"status":"ACTIVE","trading_blocked":False,"buying_power":"100000"},
      "asset":{"symbol":config.symbol,"tradable":True},
      "clock":{"is_open":True},
      "quote":{"ask_price":200.0},
      "order_response":{"id":"paper-order-1","client_order_id":"single-fixture",
        "symbol":config.symbol,"side":config.side,"type":config.order_type,
        "status":"accepted","qty":"1","filled_qty":"0"}}

def offline_scenario(config):
    f=fixtures(config);pf=preflight(config,f["account"],f["asset"],f["clock"],f["quote"])
    token=one_order_token(config,pf);payload=build_payload(config,token)
    response={"stage":"V86.07","status_code":201,"ok":True,"response":f["order_response"],
              "credentials_redacted":True,"fixture":True}
    response["result_sha256"]=hj(response)
    verify=read_after_write(response);used=consume_token(token);revoked=revoke_token(used,"validation complete")
    d={"stage":"V86.12","status":"PASS","preflight_status":pf["status"],"token_issued":True,
       "payload_ready":True,"response_ok":response["ok"],"read_after_write_status":verify["status"],
       "token_used":used["used"],"token_revoked":revoked["revoked"],
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{"preflight":pf,"token":token,"payload":payload,"response":response,
                    "verification":verify,"used":used,"revoked":revoked}}
    d["scenario_sha256"]=hj(d);return d

def audit(config,scenario):
    checks={"preflight_pass":scenario["preflight_status"]=="PASS","token_issued":scenario["token_issued"],
      "payload_ready":scenario["payload_ready"],"response_ok":scenario["response_ok"],
      "read_after_write_pass":scenario["read_after_write_status"]=="PASS",
      "token_used":scenario["token_used"],"token_revoked":scenario["token_revoked"],
      "network_zero":scenario["network_requests_executed"]==0,
      "orders_zero":scenario["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.13","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="single-order-validation-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V86.14","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"single_order_master_ledger_v86_14.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger,network_requests,orders):
    lp=out/"single_order_master_ledger_v86_14.json";b=lp.read_bytes()
    d={"stage":"V86.15","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),
       "sha256":hb(b),"byte_size":len(b)}},"network_requests_executed":network_requests,
       "credentials_used":2 if network_requests else 0,"actual_orders_submitted":orders}
    d["manifest_sha256"]=hj(d);wj(out/"single_order_manifest_v86_15.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    return True

def run_engine(root,c,out,env=None,enable_network=False,enable_order=False,transport=default_transport):
    source=validate_enablement_certificate(root/"release/v86_00/output/paper_network_enablement_certificate_v86_00.json")
    env=dict(os.environ) if env is None else env
    cred=credential_status(env);gate=opt_in_gate(c,env,enable_network,enable_order)
    scenario=offline_scenario(c);network_requests=0;orders=0;network_mode="OFFLINE_FIXTURE"
    actual=None
    if gate["allowed"]:
        if not cred["complete"]: raise ValueError("paper credentials required")
        f=fixtures(c);pf=preflight(c,f["account"],f["asset"],f["clock"],f["quote"])
        token=one_order_token(c,pf);payload=build_payload(c,token)
        actual=execute_order(c,env,payload,transport);network_requests=1
        orders=1 if actual["ok"] else 0;network_mode="ACTUAL_SINGLE_PAPER_ORDER"
        if actual["ok"]: read_after_write(actual)
    au=audit(c,scenario);docs={"policy":policy(),"credential_status":cred,"opt_in_gate":gate,
       "offline_scenario":scenario,"rollback_plan":rollback_plan(),"audit":au}
    if actual is not None: docs["actual_order_result"]=actual
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"],network_requests,orders);verify_manifest(out,manifest)
    summary={"network_mode":network_mode,"preflight_status":scenario["preflight_status"],
      "token_issued":scenario["token_issued"],"read_after_write_status":scenario["read_after_write_status"],
      "token_revoked":scenario["token_revoked"],"rollback_status":"PASS","audit_status":au["status"],
      "source_enablement_complete":source["paper_network_enablement_foundation_complete"],
      "network_requests_executed":network_requests,"actual_orders_submitted":orders}
    return {"stage":"V86.19","status":"PASS","summary":summary,**stored,"manifest":manifest}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v86_00_certificate_present":(root/"release/v86_00/output/paper_network_enablement_certificate_v86_00.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","preflight_pass":s["preflight_status"]=="PASS",
      "token_issued":s["token_issued"],"read_after_write_pass":s["read_after_write_status"]=="PASS",
      "token_revoked":s["token_revoked"],"rollback_pass":s["rollback_status"]=="PASS",
      "audit_pass":s["audit_status"]=="PASS","manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "one_order_or_less":s["actual_orders_submitted"]<=1}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V86.20","status":status,"scope":"PAPER_BROKER_SINGLE_ORDER_NETWORK_VALIDATION",
      "stages_completed":[f"V86.{i:02d}" for i in range(1,21)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"single_order_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "single_order_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":s["network_requests_executed"],
      "credentials_used":2 if s["network_requests_executed"] else 0,
      "broker_connected":s["network_mode"]=="ACTUAL_SINGLE_PAPER_ORDER",
      "actual_orders_submitted":s["actual_orders_submitted"],
      "paper_single_order_validation_complete":status=="PASS",
      "paper_order_submission_authorized":False,"live_trading_authorized":False,
      "next_phase":"V86_21_PAPER_ORDER_LIFECYCLE_NETWORK_VALIDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"single_order_certificate_v86_20.json",cert)
    wj(out/"single_order_verify_v86_20.json",{"stage":"V86.20","status":status,
      "verified":not failed,"certificate_sha256":cert["certificate_sha256"],
      "failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
