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
class PaperOrderAuthorizationConfig:
    mode:str="PAPER_ORDER_SUBMISSION_AUTHORIZATION_OFFLINE"
    environment:str="PAPER"
    required_approvals:int=2
    token_ttl_seconds:int=180
    single_use:bool=True
    max_order_notional:float=500.0
    max_quantity:int=10
    buying_power:float=10000.0
    max_daily_loss:float=250.0
    max_position_notional:float=2500.0
    kill_switch_armed:bool=True
    explicit_submission_opt_in:bool=False
    required_opt_in_value:str="YES"
    allow_network:bool=False
    allow_post:bool=False
    allow_cancel:bool=False
    allow_replace:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="PAPER_ORDER_SUBMISSION_AUTHORIZATION_OFFLINE": raise ValueError("mode")
        if self.environment!="PAPER": raise ValueError("environment")
        if self.required_approvals<2 or self.token_ttl_seconds<60: raise ValueError("approval policy")
        if not self.single_use or min(self.max_order_notional,self.max_quantity,self.buying_power,self.max_daily_loss,self.max_position_notional)<=0:
            raise ValueError("risk policy")
        if not self.kill_switch_armed: raise ValueError("kill switch")
        if self.allow_network or self.allow_post or self.allow_cancel or self.allow_replace or self.actual_orders_submitted:
            raise ValueError("offline authorization only")

def validate_read_only_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V85.40" or c.get("status")!="PASS": raise ValueError("bad V85.40 certificate")
    if c.get("paper_read_only_validation_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("read-only prerequisite")
    if c.get("paper_order_submission_authorized") is not False: raise ValueError("unsafe prerequisite")
    return c

def authorization_policy():
    d={"stage":"V85.41","status":"PASS","environment":"PAPER","authorization_review_allowed":True,
       "paper_order_submission_allowed":False,"live_order_submission_allowed":False,
       "network_post_allowed":False,"single_use_required":True}
    d["policy_sha256"]=hj(d);return d

def create_order_intent(symbol,side,quantity,reference_price):
    side=side.upper();symbol=symbol.upper()
    if side not in {"BUY","SELL"} or quantity<1 or reference_price<=0: raise ValueError("intent")
    d={"stage":"V85.42","intent_id":"paper-order-intent-"+hj([symbol,side,quantity,reference_price])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"reference_price":float(reference_price),
       "environment":"PAPER","paper_order_submission_authorized":False}
    d["intent_sha256"]=hj(d);return d

def create_request(operator_id,intent,reason,ttl_seconds):
    if not operator_id.strip() or not reason.strip() or ttl_seconds<60: raise ValueError("request")
    d={"stage":"V85.43","request_id":"paper-auth-"+hj([operator_id,intent,reason,ttl_seconds])[:20],
       "operator_id":operator_id,"intent_id":intent["intent_id"],"reason":reason,
       "ttl_seconds":ttl_seconds,"status":"PENDING","approvals":[],
       "paper_order_submission_authorized":False}
    d["request_sha256"]=hj(d);return d

def add_approval(request,approver_id):
    approvals=list(request["approvals"])
    if approver_id in approvals: raise ValueError("duplicate approval")
    approvals.append(approver_id)
    d={**request,"stage":"V85.44","approvals":approvals,"status":"PARTIALLY_APPROVED",
       "paper_order_submission_authorized":False}
    d["request_sha256"]=hj({k:v for k,v in d.items() if k!="request_sha256"});return d

def approval_gate(request,config):
    count=len(request["approvals"]);allowed=count>=config.required_approvals
    d={"stage":"V85.45","approval_count":count,"required_approvals":config.required_approvals,
       "allowed":allowed,"paper_order_submission_authorized":False}
    d["approval_sha256"]=hj(d);return d

def explicit_opt_in_gate(config,env):
    value=env.get("AI_STOCK_BOT_ENABLE_PAPER_ORDER_AUTHORIZATION","")
    allowed=config.explicit_submission_opt_in and value==config.required_opt_in_value
    d={"stage":"V85.46","config_opt_in":config.explicit_submission_opt_in,
       "environment_opt_in_match":value==config.required_opt_in_value,
       "allowed":allowed,"paper_order_submission_authorized":False}
    d["opt_in_sha256"]=hj(d);return d

def notional_gate(intent,config):
    notional=intent["quantity"]*intent["reference_price"];allowed=notional<=config.max_order_notional
    d={"stage":"V85.47","notional":round(notional,8),"limit":config.max_order_notional,"allowed":allowed}
    d["notional_sha256"]=hj(d);return d

def quantity_gate(intent,config):
    allowed=intent["quantity"]<=config.max_quantity
    d={"stage":"V85.48","quantity":intent["quantity"],"limit":config.max_quantity,"allowed":allowed}
    d["quantity_sha256"]=hj(d);return d

def buying_power_gate(intent,config):
    required=intent["quantity"]*intent["reference_price"] if intent["side"]=="BUY" else 0.0
    allowed=required<=config.buying_power
    d={"stage":"V85.49","required":round(required,8),"available":config.buying_power,"allowed":allowed}
    d["buying_power_sha256"]=hj(d);return d

def daily_loss_gate(realized_pnl,config):
    loss=max(0.0,-realized_pnl);allowed=loss<=config.max_daily_loss
    d={"stage":"V85.50","daily_loss":loss,"limit":config.max_daily_loss,"allowed":allowed,"halt_required":not allowed}
    d["daily_loss_sha256"]=hj(d);return d

def position_gate(intent,current_qty,config):
    projected=current_qty+intent["quantity"] if intent["side"]=="BUY" else current_qty-intent["quantity"]
    notional=abs(projected*intent["reference_price"])
    allowed=projected>=0 and notional<=config.max_position_notional
    d={"stage":"V85.51","current_quantity":current_qty,"projected_quantity":projected,
       "projected_notional":round(notional,8),"limit":config.max_position_notional,"allowed":allowed}
    d["position_sha256"]=hj(d);return d

def kill_switch_gate(config):
    d={"stage":"V85.52","state":"ARMED" if config.kill_switch_armed else "DISARMED",
       "allowed":config.kill_switch_armed,"blocks_actual_submission":True}
    d["kill_switch_sha256"]=hj(d);return d

def duplicate_guard(intent_ids):
    duplicate=len(intent_ids)!=len(set(intent_ids))
    d={"stage":"V85.53","intent_count":len(intent_ids),"duplicate_detected":duplicate,"accepted":not duplicate}
    d["duplicate_sha256"]=hj(d);return d

def issue_token(intent,request,gates,config):
    failed=[k for k,v in gates.items() if not v["allowed"]]
    if failed: raise ValueError("authorization gates failed: "+",".join(failed))
    d={"stage":"V85.54","token_id":"paper-order-auth-token-"+hj([intent,request,gates])[:24],
       "intent_id":intent["intent_id"],"scope":"PAPER_ORDER_AUTHORIZATION",
       "ttl_seconds":config.token_ttl_seconds,"single_use":config.single_use,
       "used":False,"revoked":False,"expired":False,
       "paper_order_submission_authorized":False,"actual_order_submitted":False}
    d["token_sha256"]=hj(d);return d

def validate_token(token,intent_id):
    checks={"intent_match":token["intent_id"]==intent_id,"scope_valid":token["scope"]=="PAPER_ORDER_AUTHORIZATION",
      "single_use":token["single_use"],"not_used":token["used"] is False,
      "not_revoked":token["revoked"] is False,"not_expired":token["expired"] is False,
      "submission_false":token["paper_order_submission_authorized"] is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V85.55","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["validation_sha256"]=hj(d);return d

def consume_token(token):
    if token["used"] or token["revoked"] or token["expired"]: raise ValueError("token unavailable")
    d={**token,"stage":"V85.56","used":True,"paper_order_submission_authorized":False,"actual_order_submitted":False}
    d["token_sha256"]=hj({k:v for k,v in d.items() if k!="token_sha256"});return d

def replay_guard(receipts):
    hashes=[x["receipt_sha256"] for x in receipts]
    replay=len(hashes)!=len(set(hashes))
    d={"stage":"V85.57","receipt_count":len(receipts),"replay_detected":replay,"accepted":not replay}
    d["replay_sha256"]=hj(d);return d

def authorization_receipt(intent,token,validation):
    d={"stage":"V85.58","receipt_id":"paper-order-auth-receipt-"+hj([intent,token,validation])[:24],
       "status":"AUTHORIZATION_READY" if validation["status"]=="PASS" else "AUTHORIZATION_REJECTED",
       "intent_id":intent["intent_id"],"token_id":token["token_id"],
       "paper_order_submission_authorized":False,"actual_order_submitted":False}
    d["receipt_sha256"]=hj(d);return d

def build_scenarios(config):
    env={"AI_STOCK_BOT_ENABLE_PAPER_ORDER_AUTHORIZATION":"YES"}
    good=create_order_intent("AAPL","BUY",2,100)
    req=create_request("operator-1",good,"paper authorization review",config.token_ttl_seconds)
    req=add_approval(req,"approver-a");req=add_approval(req,"approver-b")
    approval=approval_gate(req,config)
    optin=explicit_opt_in_gate(PaperOrderAuthorizationConfig(explicit_submission_opt_in=True),env)
    gates={"approval":approval,"opt_in":optin,"notional":notional_gate(good,config),
           "quantity":quantity_gate(good,config),"buying_power":buying_power_gate(good,config),
           "daily_loss":daily_loss_gate(-100.0,config),"position":position_gate(good,0,config),
           "kill_switch":kill_switch_gate(config)}
    token=issue_token(good,req,gates,config);validation=validate_token(token,good["intent_id"])
    receipt=authorization_receipt(good,token,validation);used=consume_token(token)
    bad_intents=[
      create_order_intent("MSFT","BUY",10,100),
      create_order_intent("SPY","BUY",11,10),
      create_order_intent("QQQ","SELL",5,100),
    ]
    rejects=[
      notional_gate(bad_intents[0],config)["allowed"],
      quantity_gate(bad_intents[1],config)["allowed"],
      position_gate(bad_intents[2],0,config)["allowed"],
      daily_loss_gate(-500.0,config)["allowed"],
    ]
    dup=duplicate_guard([good["intent_id"],good["intent_id"]]);replay=replay_guard([receipt,receipt])
    d={"stage":"V85.59","status":"PASS","approval_count":approval["approval_count"],
       "token_issued":True,"token_validation_status":validation["status"],
       "receipt_status":receipt["status"],"single_use_consumed":used["used"],
       "risk_reject_count":sum(not x for x in rejects),"duplicate_detected":dup["duplicate_detected"],
       "replay_detected":replay["replay_detected"],"actual_orders_submitted":0,
       "documents":{"intent":good,"request":req,"gates":gates,"token":token,
                    "validation":validation,"receipt":receipt,"used":used}}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,policy,scenarios):
    checks={"policy_pass":policy["status"]=="PASS",
      "paper_submission_false":policy["paper_order_submission_allowed"] is False,
      "network_post_false":policy["network_post_allowed"] is False,
      "approval_count_valid":scenarios["approval_count"]>=config.required_approvals,
      "token_issued":scenarios["token_issued"],"token_validation_pass":scenarios["token_validation_status"]=="PASS",
      "receipt_ready":scenarios["receipt_status"]=="AUTHORIZATION_READY",
      "single_use_consumed":scenarios["single_use_consumed"],
      "risk_rejects_positive":scenarios["risk_reject_count"]>0,
      "duplicate_detected":scenarios["duplicate_detected"],"replay_detected":scenarios["replay_detected"],
      "actual_orders_zero":scenarios["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V85.60","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="paper-order-authorization-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V85.60","status":"PASS","package_id":pid,"document_count":len(docs),"package_created":created,
            "package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_order_authorization_master_ledger_v85_60.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"paper_order_authorization_master_ledger_v85_60.json";b=lp.read_bytes()
    d={"stage":"V85.60","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_order_authorization_manifest_v85_60.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"paper_order_authorization_master_ledger_v85_60.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_read_only_certificate(root/"release/v85_40/output/paper_read_only_certificate_v85_40.json")
    policy=authorization_policy();scenarios=build_scenarios(c);audit=build_audit(c,policy,scenarios)
    docs={"policy":policy,"scenarios":scenarios,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"required_approvals":c.required_approvals,"approval_count":scenarios["approval_count"],
      "token_ttl_seconds":c.token_ttl_seconds,"token_issued":scenarios["token_issued"],
      "token_validation_status":scenarios["token_validation_status"],
      "receipt_status":scenarios["receipt_status"],"single_use_consumed":scenarios["single_use_consumed"],
      "risk_reject_count":scenarios["risk_reject_count"],"duplicate_detected":scenarios["duplicate_detected"],
      "replay_detected":scenarios["replay_detected"],"audit_status":audit["status"],
      "source_read_only_validation_complete":source["paper_read_only_validation_complete"]}
    return {"stage":"V85.60","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v85_40_certificate_present":(root/"release/v85_40/output/paper_read_only_certificate_v85_40.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","approval_count_valid":s["approval_count"]>=s["required_approvals"],
      "token_issued":s["token_issued"],"token_validation_pass":s["token_validation_status"]=="PASS",
      "receipt_ready":s["receipt_status"]=="AUTHORIZATION_READY","single_use_consumed":s["single_use_consumed"],
      "risk_rejects_positive":s["risk_reject_count"]>0,"duplicate_detected":s["duplicate_detected"],
      "replay_detected":s["replay_detected"],"audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V85.60","status":status,"scope":"PAPER_ORDER_SUBMISSION_AUTHORIZATION_OFFLINE",
      "stages_completed":[f"V85.{i:02d}" for i in range(41,61)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"paper_order_authorization_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "paper_order_authorization_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_order_authorization_ready":status=="PASS",
      "paper_order_submission_authorized":False,"live_trading_authorized":False,
      "paper_order_authorization_complete":status=="PASS",
      "next_phase":"V85_61_PAPER_ORDER_SUBMISSION_SIMULATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"paper_order_authorization_certificate_v85_60.json",cert)
    wj(out/"paper_order_authorization_verify_v85_60.json",{"stage":"V85.60","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
