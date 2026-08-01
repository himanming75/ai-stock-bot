from __future__ import annotations
from dataclasses import dataclass, asdict
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
class LiveOrderAuthorizationConfig:
    mode:str="LIVE_ORDER_AUTHORIZATION_OFFLINE"
    environment:str="LIVE"
    required_approvals:int=3
    token_ttl_seconds:int=180
    single_use:bool=True
    max_order_notional:float=500.0
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="LIVE_ORDER_AUTHORIZATION_OFFLINE": raise ValueError("safe mode")
        if self.environment!="LIVE": raise ValueError("live environment")
        if self.required_approvals<3 or self.token_ttl_seconds<60: raise ValueError("approval policy")
        if not self.single_use or self.max_order_notional<=0: raise ValueError("token policy")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline authorization only")

def validate_gate_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V84.40" or c.get("status")!="PASS": raise ValueError("bad V84.40 certificate")
    if c.get("live_order_gate_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("gate prerequisite")
    if c.get("live_order_submission_authorized") is not False or c.get("live_trading_authorized") is not False:
        raise ValueError("unsafe prerequisite")
    return c

def authorization_policy():
    d={"stage":"V84.41","status":"PASS","environment":"LIVE",
       "review_authorization_allowed":True,"submission_authorization_allowed":False,
       "live_trading_authorization_allowed":False,"single_use_required":True}
    d["policy_sha256"]=hj(d);return d

def create_request(operator_id,intent_id,reason,ttl_seconds):
    if not operator_id.strip() or not intent_id.strip() or not reason.strip() or ttl_seconds<60: raise ValueError("request")
    d={"stage":"V84.42","request_id":"live-auth-"+hj([operator_id,intent_id,reason,ttl_seconds])[:20],
       "operator_id":operator_id,"intent_id":intent_id,"reason":reason,"ttl_seconds":ttl_seconds,
       "status":"PENDING","live_order_submission_authorized":False}
    d["request_sha256"]=hj(d);return d

def add_approval(request,approver_id):
    approvals=list(request.get("approvals",[]))
    if approver_id in approvals: raise ValueError("duplicate approval")
    approvals.append(approver_id)
    d={**request,"stage":"V84.43","approvals":approvals,"status":"PARTIALLY_APPROVED",
       "live_order_submission_authorized":False}
    d["request_sha256"]=hj({k:v for k,v in d.items() if k!="request_sha256"});return d

def evaluate_request(request,config):
    count=len(request.get("approvals",[]));met=count>=config.required_approvals
    d={"stage":"V84.44","approval_count":count,"required_approvals":config.required_approvals,
       "threshold_met":met,"token_issuance_allowed":met,
       "live_order_submission_authorized":False}
    d["evaluation_sha256"]=hj(d);return d

def scope_contract():
    scopes={
      "LIVE_ORDER_REVIEW":{"preview":True,"authorize":False,"submit":False,"network":False},
      "LIVE_ORDER_AUTHORIZATION":{"preview":True,"authorize":True,"submit":False,"network":False},
    }
    d={"stage":"V84.45","scopes":scopes,"scope_count":len(scopes),
       "submit_capability_count":sum(v["submit"] for v in scopes.values()),
       "network_capability_count":sum(v["network"] for v in scopes.values())}
    d["scope_sha256"]=hj(d);return d

def issue_token(request,evaluation,config):
    if not evaluation["token_issuance_allowed"]: raise ValueError("insufficient approvals")
    d={"stage":"V84.46","token_id":"live-auth-token-"+hj([request,evaluation])[:24],
       "request_id":request["request_id"],"intent_id":request["intent_id"],
       "scope":"LIVE_ORDER_AUTHORIZATION","ttl_seconds":config.token_ttl_seconds,
       "single_use":config.single_use,"used":False,"revoked":False,"expired":False,
       "live_order_submission_authorized":False,"live_trading_authorized":False}
    d["token_sha256"]=hj(d);return d

def validate_token(token,intent_id):
    checks={"intent_match":token["intent_id"]==intent_id,"scope_valid":token["scope"]=="LIVE_ORDER_AUTHORIZATION",
      "single_use":token["single_use"],"not_used":token["used"] is False,"not_revoked":token["revoked"] is False,
      "not_expired":token["expired"] is False,"submit_false":token["live_order_submission_authorized"] is False,
      "live_false":token["live_trading_authorized"] is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.47","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["validation_sha256"]=hj(d);return d

def consume_token(token):
    if token["used"] or token["revoked"] or token["expired"]: raise ValueError("token unavailable")
    d={**token,"stage":"V84.48","used":True,"live_order_submission_authorized":False,
       "live_trading_authorized":False}
    d["token_sha256"]=hj({k:v for k,v in d.items() if k!="token_sha256"});return d

def revoke_token(token,reason):
    if not reason.strip(): raise ValueError("reason")
    d={**token,"stage":"V84.49","revoked":True,"revoke_reason":reason,
       "live_order_submission_authorized":False,"live_trading_authorized":False}
    d["token_sha256"]=hj({k:v for k,v in d.items() if k!="token_sha256"});return d

def expire_token(token):
    d={**token,"stage":"V84.50","expired":True,"live_order_submission_authorized":False,
       "live_trading_authorized":False}
    d["token_sha256"]=hj({k:v for k,v in d.items() if k!="token_sha256"});return d

def duplicate_guard(token_ids):
    duplicate=len(token_ids)!=len(set(token_ids))
    d={"stage":"V84.51","token_count":len(token_ids),"duplicate_detected":duplicate,"accepted":not duplicate}
    d["duplicate_sha256"]=hj(d);return d

def replay_guard(receipts):
    hashes=[x["receipt_sha256"] for x in receipts]
    duplicate=len(hashes)!=len(set(hashes))
    d={"stage":"V84.52","receipt_count":len(receipts),"replay_detected":duplicate,"accepted":not duplicate}
    d["replay_sha256"]=hj(d);return d

def authorization_receipt(token,validation):
    d={"stage":"V84.53","receipt_id":"live-auth-receipt-"+hj([token,validation])[:24],
       "status":"AUTHORIZATION_READY" if validation["status"]=="PASS" else "AUTHORIZATION_REJECTED",
       "token_id":token["token_id"],"intent_id":token["intent_id"],
       "scope":token["scope"],"live_order_submission_authorized":False,
       "live_trading_authorized":False,"actual_order_submitted":False}
    d["receipt_sha256"]=hj(d);return d

def state_machine():
    transitions={"LOCKED":["REQUESTED"],"REQUESTED":["PARTIALLY_APPROVED","DENIED"],
      "PARTIALLY_APPROVED":["TOKEN_ISSUED","DENIED"],"TOKEN_ISSUED":["USED","REVOKED","EXPIRED"],
      "USED":[],"REVOKED":[],"EXPIRED":[],"DENIED":[]}
    d={"stage":"V84.54","initial_state":"LOCKED","transitions":transitions,
       "submit_enabled_state_present":False,"live_enabled_state_present":False}
    d["state_machine_sha256"]=hj(d);return d

def build_scenarios(config):
    req=create_request("operator-1","live-intent-001","live authorization review",config.token_ttl_seconds)
    for a in ("approver-a","approver-b","approver-c"): req=add_approval(req,a)
    evaluation=evaluate_request(req,config);token=issue_token(req,evaluation,config)
    validation=validate_token(token,"live-intent-001");receipt=authorization_receipt(token,validation)
    used=consume_token(token);revoked=revoke_token(token,"operator cancel");expired=expire_token(token)
    dup=duplicate_guard([token["token_id"],token["token_id"]]);replay=replay_guard([receipt,receipt])
    bad_validation=validate_token(token,"wrong-intent")
    d={"stage":"V84.55","status":"PASS","approval_count":evaluation["approval_count"],
       "token_issued":True,"token_validation_status":validation["status"],
       "bad_token_validation_status":bad_validation["status"],
       "receipt_status":receipt["status"],"single_use_consumed":used["used"],
       "revocation_supported":revoked["revoked"],"expiration_supported":expired["expired"],
       "duplicate_detected":dup["duplicate_detected"],"replay_detected":replay["replay_detected"],
       "documents":{"request":req,"evaluation":evaluation,"token":token,"validation":validation,
         "bad_validation":bad_validation,"receipt":receipt,"used":used,"revoked":revoked,
         "expired":expired,"duplicate":dup,"replay":replay}}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,policy,scopes,machine,scenarios):
    checks={"policy_pass":policy["status"]=="PASS",
      "submission_authorization_false":policy["submission_authorization_allowed"] is False,
      "live_trading_authorization_false":policy["live_trading_authorization_allowed"] is False,
      "submit_capabilities_zero":scopes["submit_capability_count"]==0,
      "network_capabilities_zero":scopes["network_capability_count"]==0,
      "approval_count_valid":scenarios["approval_count"]>=config.required_approvals,
      "token_issued":scenarios["token_issued"],"token_validation_pass":scenarios["token_validation_status"]=="PASS",
      "bad_validation_fail":scenarios["bad_token_validation_status"]=="FAIL",
      "receipt_ready":scenarios["receipt_status"]=="AUTHORIZATION_READY",
      "single_use_consumed":scenarios["single_use_consumed"],
      "revocation_supported":scenarios["revocation_supported"],
      "expiration_supported":scenarios["expiration_supported"],
      "duplicate_detected":scenarios["duplicate_detected"],"replay_detected":scenarios["replay_detected"],
      "state_machine_no_submit":machine["submit_enabled_state_present"] is False,
      "state_machine_no_live":machine["live_enabled_state_present"] is False,
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.56","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="live-order-authorization-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V84.57","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"live_order_authorization_master_ledger_v84_57.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"live_order_authorization_master_ledger_v84_57.json";b=lp.read_bytes()
    d={"stage":"V84.58","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"live_order_authorization_manifest_v84_58.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"live_order_authorization_master_ledger_v84_57.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_gate_certificate(root/"release/v84_40/output/live_order_gate_certificate_v84_40.json")
    policy=authorization_policy();scopes=scope_contract();machine=state_machine();scenarios=build_scenarios(c)
    audit=build_audit(c,policy,scopes,machine,scenarios)
    docs={"policy":policy,"scope_contract":scopes,"state_machine":machine,"scenarios":scenarios,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"required_approvals":c.required_approvals,"approval_count":scenarios["approval_count"],
      "token_ttl_seconds":c.token_ttl_seconds,"token_issued":scenarios["token_issued"],
      "token_validation_status":scenarios["token_validation_status"],
      "bad_token_validation_status":scenarios["bad_token_validation_status"],
      "receipt_status":scenarios["receipt_status"],"single_use_consumed":scenarios["single_use_consumed"],
      "revocation_supported":scenarios["revocation_supported"],"expiration_supported":scenarios["expiration_supported"],
      "duplicate_detected":scenarios["duplicate_detected"],"replay_detected":scenarios["replay_detected"],
      "submit_capability_count":scopes["submit_capability_count"],
      "network_capability_count":scopes["network_capability_count"],
      "audit_status":audit["status"],"source_live_order_gate_complete":source["live_order_gate_complete"]}
    return {"stage":"V84.59","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v84_40_certificate_present":(root/"release/v84_40/output/live_order_gate_certificate_v84_40.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","approval_count_valid":s["approval_count"]>=s["required_approvals"],
      "token_issued":s["token_issued"],"token_validation_pass":s["token_validation_status"]=="PASS",
      "bad_validation_fail":s["bad_token_validation_status"]=="FAIL","receipt_ready":s["receipt_status"]=="AUTHORIZATION_READY",
      "single_use_consumed":s["single_use_consumed"],"revocation_supported":s["revocation_supported"],
      "expiration_supported":s["expiration_supported"],"duplicate_detected":s["duplicate_detected"],
      "replay_detected":s["replay_detected"],"submit_capabilities_zero":s["submit_capability_count"]==0,
      "network_capabilities_zero":s["network_capability_count"]==0,"audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V84.60","status":status,"scope":"OFFLINE_LIVE_ORDER_AUTHORIZATION_FOUNDATION",
      "stages_completed":[f"V84.{i:02d}" for i in range(41,61)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"live_order_authorization_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "live_order_authorization_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "live_order_authorization_ready":status=="PASS",
      "live_order_submission_authorized":False,"live_trading_authorized":False,
      "live_order_authorization_foundation_complete":status=="PASS",
      "next_phase":"V84_61_LIVE_ORDER_SUBMISSION_SIMULATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"live_order_authorization_certificate_v84_60.json",cert)
    wj(out/"live_order_authorization_verify_v84_60.json",{"stage":"V84.60","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
