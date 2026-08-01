from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping
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
class PaperBrokerNetworkEnablementConfig:
    mode:str="PAPER_BROKER_NETWORK_ENABLEMENT_OFFLINE"
    environment:str="PAPER"
    required_approvals:int=2
    session_ttl_seconds:int=300
    one_order_limit:int=1
    max_order_notional:float=500.0
    explicit_network_opt_in:bool=False
    required_opt_in_value:str="YES"
    kill_switch_armed:bool=True
    emergency_stop_ready:bool=True
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    allow_order_cancel:bool=False
    allow_order_replace:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="PAPER_BROKER_NETWORK_ENABLEMENT_OFFLINE": raise ValueError("mode")
        if self.environment!="PAPER": raise ValueError("environment")
        if self.required_approvals<2 or self.session_ttl_seconds<60: raise ValueError("approval/session")
        if self.one_order_limit!=1 or self.max_order_notional<=0: raise ValueError("order limit")
        if not self.kill_switch_armed or not self.emergency_stop_ready: raise ValueError("safety state")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.allow_order_cancel or self.allow_order_replace or self.actual_orders_submitted:
            raise ValueError("offline enablement only")

def validate_submission_sim_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V85.80" or c.get("status")!="PASS": raise ValueError("bad V85.80 certificate")
    if c.get("paper_order_submission_simulation_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("simulation prerequisite")
    if c.get("paper_order_submission_authorized") is not False: raise ValueError("unsafe prerequisite")
    return c

def enablement_policy():
    d={"stage":"V85.81","status":"PASS","environment":"PAPER",
       "network_enablement_review_allowed":True,"network_enabled":False,
       "order_submission_enabled":False,"live_trading_enabled":False}
    d["policy_sha256"]=hj(d);return d

def capability_registry():
    caps={"account_read":True,"positions_read":True,"orders_read":True,"clock_read":True,
          "assets_read":True,"market_data_read":True,"order_submit":False,
          "order_cancel":False,"order_replace":False}
    d={"stage":"V85.82","capabilities":caps,
       "read_capability_count":sum(v for k,v in caps.items() if k.endswith("_read")),
       "write_capability_count":sum(v for k,v in caps.items() if k.startswith("order_"))}
    d["registry_sha256"]=hj(d);return d

def credential_scope_contract():
    d={"stage":"V85.83","required_names":["APCA_API_KEY_ID","APCA_API_SECRET_KEY"],
       "allowed_environment":"PAPER","read_scope":True,"write_scope":False,
       "secret_values_persisted":False,"credentials_used":0}
    d["credential_scope_sha256"]=hj(d);return d

def inspect_credentials(env:Mapping[str,str]):
    key=bool(env.get("APCA_API_KEY_ID","").strip());secret=bool(env.get("APCA_API_SECRET_KEY","").strip())
    d={"stage":"V85.84","api_key_present":key,"api_secret_present":secret,
       "complete":key and secret,"values_redacted":True,"credentials_used":0}
    d["credential_status_sha256"]=hj(d);return d

def explicit_opt_in_gate(config,env):
    value=env.get("AI_STOCK_BOT_ENABLE_PAPER_NETWORK_WRITE_FOUNDATION","")
    allowed=config.explicit_network_opt_in and value==config.required_opt_in_value
    d={"stage":"V85.85","config_opt_in":config.explicit_network_opt_in,
       "environment_opt_in_match":value==config.required_opt_in_value,
       "enablement_review_allowed":allowed,"network_enabled":False}
    d["opt_in_sha256"]=hj(d);return d

def approval_request(operator_id,reason):
    if not operator_id.strip() or not reason.strip(): raise ValueError("request")
    d={"stage":"V85.86","request_id":"paper-network-enable-"+hj([operator_id,reason])[:20],
       "operator_id":operator_id,"reason":reason,"approvals":[],"status":"PENDING",
       "network_enabled":False}
    d["request_sha256"]=hj(d);return d

def add_approval(request,approver):
    approvals=list(request["approvals"])
    if approver in approvals: raise ValueError("duplicate approval")
    approvals.append(approver)
    d={**request,"stage":"V85.87","approvals":approvals,"status":"PARTIALLY_APPROVED","network_enabled":False}
    d["request_sha256"]=hj({k:v for k,v in d.items() if k!="request_sha256"});return d

def approval_gate(request,config):
    count=len(request["approvals"]);allowed=count>=config.required_approvals
    d={"stage":"V85.88","approval_count":count,"required_approvals":config.required_approvals,
       "allowed":allowed,"network_enabled":False}
    d["approval_sha256"]=hj(d);return d

def session_contract(config):
    d={"stage":"V85.89","session_ttl_seconds":config.session_ttl_seconds,
       "single_session":True,"one_order_limit":config.one_order_limit,
       "session_revoke_supported":True,"network_session_created":False}
    d["session_contract_sha256"]=hj(d);return d

def kill_switch_gate(config):
    d={"stage":"V85.90","kill_switch_state":"ARMED" if config.kill_switch_armed else "DISARMED",
       "emergency_stop_state":"READY" if config.emergency_stop_ready else "NOT_READY",
       "allowed":config.kill_switch_armed and config.emergency_stop_ready,
       "blocks_network_and_orders":True}
    d["kill_switch_sha256"]=hj(d);return d

def one_order_limit_gate(requested_count,config):
    allowed=0<=requested_count<=config.one_order_limit
    d={"stage":"V85.91","requested_order_count":requested_count,
       "limit":config.one_order_limit,"allowed":allowed}
    d["one_order_sha256"]=hj(d);return d

def notional_gate(notional,config):
    allowed=0<notional<=config.max_order_notional
    d={"stage":"V85.92","requested_notional":notional,
       "limit":config.max_order_notional,"allowed":allowed}
    d["notional_sha256"]=hj(d);return d

def issue_enablement_receipt(request,gates,config):
    failed=[k for k,v in gates.items() if not v["allowed"]]
    if failed: raise ValueError("enablement gates failed: "+",".join(failed))
    d={"stage":"V85.93","receipt_id":"paper-network-enablement-"+hj([request,gates])[:24],
       "status":"ENABLEMENT_FOUNDATION_READY","scope":"PAPER_NETWORK_WRITE_FOUNDATION",
       "session_ttl_seconds":config.session_ttl_seconds,"one_order_limit":config.one_order_limit,
       "network_enabled":False,"paper_order_submission_authorized":False}
    d["receipt_sha256"]=hj(d);return d

def revoke_receipt(receipt,reason):
    if not reason.strip(): raise ValueError("reason")
    d={**receipt,"stage":"V85.94","status":"REVOKED","revoke_reason":reason,
       "network_enabled":False,"paper_order_submission_authorized":False}
    d["receipt_sha256"]=hj({k:v for k,v in d.items() if k!="receipt_sha256"});return d

def rollback_plan():
    d={"stage":"V85.95","status":"PASS","rollback_target":"V85.80",
       "disable_network":True,"disable_credentials":True,"disable_trading_client":True,
       "disable_order_submission":True,"manual_action_required":True}
    d["rollback_sha256"]=hj(d);return d

def build_scenarios(config):
    env={"AI_STOCK_BOT_ENABLE_PAPER_NETWORK_WRITE_FOUNDATION":"YES"}
    cfg=PaperBrokerNetworkEnablementConfig(explicit_network_opt_in=True)
    request=approval_request("operator-1","paper network foundation review")
    request=add_approval(request,"approver-a");request=add_approval(request,"approver-b")
    gates={"approval":approval_gate(request,cfg),
           "opt_in":{"allowed":explicit_opt_in_gate(cfg,env)["enablement_review_allowed"]},
           "kill_switch":kill_switch_gate(cfg),
           "one_order":one_order_limit_gate(1,cfg),
           "notional":notional_gate(200.0,cfg)}
    receipt=issue_enablement_receipt(request,gates,cfg);revoked=revoke_receipt(receipt,"operator cancel")
    rejects=[one_order_limit_gate(2,cfg)["allowed"],notional_gate(1000.0,cfg)["allowed"]]
    d={"stage":"V85.96","status":"PASS","approval_count":len(request["approvals"]),
       "enablement_receipt_status":receipt["status"],"revocation_supported":revoked["status"]=="REVOKED",
       "risk_reject_count":sum(not x for x in rejects),"network_enabled":False,
       "actual_orders_submitted":0,"documents":{"request":request,"gates":gates,"receipt":receipt,"revoked":revoked}}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,policy,registry,scope,scenarios,rollback):
    checks={"policy_pass":policy["status"]=="PASS","network_false":policy["network_enabled"] is False,
      "order_submit_false":policy["order_submission_enabled"] is False,
      "read_capabilities_positive":registry["read_capability_count"]>0,
      "write_capabilities_zero":registry["write_capability_count"]==0,
      "credential_write_scope_false":scope["write_scope"] is False,
      "approval_count_valid":scenarios["approval_count"]>=config.required_approvals,
      "receipt_ready":scenarios["enablement_receipt_status"]=="ENABLEMENT_FOUNDATION_READY",
      "revocation_supported":scenarios["revocation_supported"],
      "risk_rejects_positive":scenarios["risk_reject_count"]>0,
      "rollback_pass":rollback["status"]=="PASS","actual_orders_zero":scenarios["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V85.97","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="paper-network-enablement-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V85.98","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_network_enablement_master_ledger_v85_98.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"paper_network_enablement_master_ledger_v85_98.json";b=lp.read_bytes()
    d={"stage":"V85.99","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),
       "sha256":hb(b),"byte_size":len(b)}},"network_requests_executed":0,
       "credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_network_enablement_manifest_v85_99.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"paper_network_enablement_master_ledger_v85_98.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_submission_sim_certificate(root/"release/v85_80/output/paper_order_submission_sim_certificate_v85_80.json")
    policy=enablement_policy();registry=capability_registry();scope=credential_scope_contract()
    session=session_contract(c);rollback=rollback_plan();scenarios=build_scenarios(c)
    audit=build_audit(c,policy,registry,scope,scenarios,rollback)
    docs={"policy":policy,"capability_registry":registry,"credential_scope":scope,
          "session_contract":session,"rollback_plan":rollback,"scenarios":scenarios,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"approval_count":scenarios["approval_count"],"required_approvals":c.required_approvals,
      "enablement_receipt_status":scenarios["enablement_receipt_status"],
      "revocation_supported":scenarios["revocation_supported"],"risk_reject_count":scenarios["risk_reject_count"],
      "read_capability_count":registry["read_capability_count"],"write_capability_count":registry["write_capability_count"],
      "session_ttl_seconds":c.session_ttl_seconds,"one_order_limit":c.one_order_limit,
      "rollback_status":rollback["status"],"audit_status":audit["status"],
      "source_submission_sim_complete":source["paper_order_submission_simulation_complete"]}
    return {"stage":"V86.00","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v85_80_certificate_present":(root/"release/v85_80/output/paper_order_submission_sim_certificate_v85_80.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","approval_count_valid":s["approval_count"]>=s["required_approvals"],
      "receipt_ready":s["enablement_receipt_status"]=="ENABLEMENT_FOUNDATION_READY",
      "revocation_supported":s["revocation_supported"],"risk_rejects_positive":s["risk_reject_count"]>0,
      "read_capabilities_positive":s["read_capability_count"]>0,"write_capabilities_zero":s["write_capability_count"]==0,
      "one_order_limit_one":s["one_order_limit"]==1,"rollback_pass":s["rollback_status"]=="PASS",
      "audit_pass":s["audit_status"]=="PASS","manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V86.00","status":status,"scope":"PAPER_BROKER_NETWORK_ENABLEMENT_FOUNDATION_OFFLINE",
      "stages_completed":[f"V85.{i:02d}" for i in range(81,100)]+["V86.00"],
      "completed_stage_count":20 if status=="PASS" else 20-len(failed),"config":asdict(c),
      "paper_network_enablement_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "paper_network_enablement_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_network_enablement_foundation_complete":status=="PASS",
      "paper_network_enabled":False,"paper_order_submission_authorized":False,
      "live_trading_authorized":False,
      "next_phase":"V86_01_PAPER_BROKER_SINGLE_ORDER_NETWORK_VALIDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"paper_network_enablement_certificate_v86_00.json",cert)
    wj(out/"paper_network_enablement_verify_v86_00.json",{"stage":"V86.00","status":status,
      "verified":not failed,"certificate_sha256":cert["certificate_sha256"],
      "failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
