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
class PaperOrderSubmissionSimulationConfig:
    mode:str="PAPER_ORDER_SUBMISSION_SIMULATION_OFFLINE"
    environment:str="PAPER"
    retry_limit:int=3
    partial_fill_ratio:float=0.5
    ack_latency_ms:int=25
    allow_network:bool=False
    allow_post:bool=False
    allow_cancel:bool=False
    allow_replace:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="PAPER_ORDER_SUBMISSION_SIMULATION_OFFLINE": raise ValueError("mode")
        if self.environment!="PAPER": raise ValueError("environment")
        if self.retry_limit<0 or not 0<self.partial_fill_ratio<1 or self.ack_latency_ms<0:
            raise ValueError("simulation policy")
        if self.allow_network or self.allow_post or self.allow_cancel or self.allow_replace or self.actual_orders_submitted:
            raise ValueError("offline simulation only")

def validate_authorization_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V85.60" or c.get("status")!="PASS": raise ValueError("bad V85.60 certificate")
    if c.get("paper_order_authorization_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("authorization prerequisite")
    if c.get("paper_order_submission_authorized") is not False:
        raise ValueError("unsafe prerequisite")
    return c

def submission_policy():
    d={"stage":"V85.61","status":"PASS","environment":"PAPER","simulation_only":True,
       "network_post_enabled":False,"broker_write_enabled":False,
       "paper_order_submission_authorized":False}
    d["policy_sha256"]=hj(d);return d

def make_intent(symbol,side,quantity,order_type="market",limit_price=None):
    symbol=symbol.upper();side=side.upper();order_type=order_type.lower()
    if side not in {"BUY","SELL"} or quantity<1 or order_type not in {"market","limit"}:
        raise ValueError("intent")
    if order_type=="limit" and (limit_price is None or limit_price<=0): raise ValueError("limit")
    d={"stage":"V85.62","intent_id":"paper-submit-"+hj([symbol,side,quantity,order_type,limit_price])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"type":order_type,
       "limit_price":limit_price,"time_in_force":"day","environment":"PAPER",
       "actual_submission_authorized":False}
    d["intent_sha256"]=hj(d);return d

def client_order_id(intent):
    d={"stage":"V85.63","intent_id":intent["intent_id"],
       "client_order_id":"psim-"+hj(intent)[:24]}
    d["client_order_id_sha256"]=hj(d);return d

def build_payload(intent,client_id):
    payload={"symbol":intent["symbol"],"qty":str(intent["quantity"]),
             "side":intent["side"].lower(),"type":intent["type"],
             "time_in_force":intent["time_in_force"],"client_order_id":client_id["client_order_id"]}
    if intent["type"]=="limit": payload["limit_price"]=str(intent["limit_price"])
    d={"stage":"V85.64","payload":payload,"simulation_payload":True,
       "network_ready":False,"post_allowed":False}
    d["payload_sha256"]=hj(d);return d

def serialize_request(payload):
    body=cj(payload["payload"]).encode("utf-8")
    d={"stage":"V85.65","content_type":"application/json","byte_size":len(body),
       "body_sha256":hb(body),"method":"POST_SIMULATION_ONLY",
       "actual_http_method_executed":False}
    d["serialization_sha256"]=hj(d);return d

def queue_order(intent,client_id):
    d={"stage":"V85.66","queue_id":"paper-sim-queue-"+hj([intent,client_id])[:20],
       "intent_id":intent["intent_id"],"client_order_id":client_id["client_order_id"],
       "status":"QUEUED_FOR_SIMULATION","network_delivery_allowed":False}
    d["queue_sha256"]=hj(d);return d

def idempotency_guard(client_ids):
    duplicate=len(client_ids)!=len(set(client_ids))
    d={"stage":"V85.67","client_order_id_count":len(client_ids),
       "duplicate_detected":duplicate,"accepted":not duplicate}
    d["idempotency_sha256"]=hj(d);return d

def ack_simulator(intent,config):
    d={"stage":"V85.68","ack_id":"paper-sim-ack-"+hj(intent)[:20],
       "ack_status":"ACK_SIMULATED","latency_ms":config.ack_latency_ms,
       "actual_broker_ack":False}
    d["ack_sha256"]=hj(d);return d

def broker_response(intent,outcome,config):
    outcome=outcome.upper()
    if outcome not in {"ACCEPTED","REJECTED","PARTIAL"}: raise ValueError("outcome")
    filled=0
    if outcome=="ACCEPTED": filled=intent["quantity"]
    elif outcome=="PARTIAL": filled=max(1,int(intent["quantity"]*config.partial_fill_ratio))
    d={"stage":"V85.69","simulated_order_id":"paper-sim-order-"+hj([intent,outcome])[:20],
       "outcome":outcome,"requested_quantity":intent["quantity"],
       "filled_quantity":filled,"remaining_quantity":intent["quantity"]-filled,
       "actual_broker_order":False}
    d["response_sha256"]=hj(d);return d

def retry_policy(config):
    d={"stage":"V85.70","retry_limit":config.retry_limit,
       "backoff_seconds":[2**i for i in range(config.retry_limit)],
       "retryable_outcomes":["REJECTED"],"network_retry_enabled":False}
    d["retry_policy_sha256"]=hj(d);return d

def retry_simulation(response,config):
    retryable=response["outcome"]=="REJECTED"
    d={"stage":"V85.71","outcome":response["outcome"],"retryable":retryable,
       "simulated_retry_attempts":config.retry_limit if retryable else 0,
       "network_retry_attempts":0}
    d["retry_sha256"]=hj(d);return d

def submission_receipt(intent,client_id,ack,response,retry):
    status={"ACCEPTED":"SIM_ACCEPTED","PARTIAL":"SIM_PARTIAL","REJECTED":"SIM_REJECTED"}[response["outcome"]]
    d={"stage":"V85.72","receipt_id":"paper-submit-receipt-"+hj([intent,client_id,ack,response,retry])[:24],
       "intent_id":intent["intent_id"],"client_order_id":client_id["client_order_id"],
       "status":status,"ack_status":ack["ack_status"],
       "filled_quantity":response["filled_quantity"],"remaining_quantity":response["remaining_quantity"],
       "simulated_retry_attempts":retry["simulated_retry_attempts"],
       "actual_order_submitted":False}
    d["receipt_sha256"]=hj(d);return d

def replay_guard(receipts):
    hashes=[r["receipt_sha256"] for r in receipts]
    replay=len(hashes)!=len(set(hashes))
    d={"stage":"V85.73","receipt_count":len(receipts),
       "replay_detected":replay,"accepted":not replay}
    d["replay_sha256"]=hj(d);return d

def state_machine():
    transitions={"CREATED":["QUEUED"],"QUEUED":["ACK_SIMULATED"],
      "ACK_SIMULATED":["SIM_ACCEPTED","SIM_PARTIAL","SIM_REJECTED"],
      "SIM_PARTIAL":["SIM_COMPLETED","SIM_CANCELED"],
      "SIM_ACCEPTED":[],"SIM_REJECTED":[],"SIM_COMPLETED":[],"SIM_CANCELED":[]}
    d={"stage":"V85.74","initial_state":"CREATED","transitions":transitions,
       "network_submit_state_present":False,"actual_order_state_present":False}
    d["state_machine_sha256"]=hj(d);return d

def deterministic_replay(intent,outcome,config):
    def one():
        cid=client_order_id(intent);payload=build_payload(intent,cid);ser=serialize_request(payload)
        queue=queue_order(intent,cid);ack=ack_simulator(intent,config)
        response=broker_response(intent,outcome,config);retry=retry_simulation(response,config)
        receipt=submission_receipt(intent,cid,ack,response,retry)
        return {"client_order_id":cid,"payload":payload,"serialization":ser,"queue":queue,
                "ack":ack,"response":response,"retry":retry,"receipt":receipt}
    a=one();b=one()
    d={"stage":"V85.75","deterministic":a==b,
       "receipt_sha256":a["receipt"]["receipt_sha256"]}
    d["determinism_sha256"]=hj(d);return d

def build_scenarios(config):
    cases=[
      (make_intent("AAPL","BUY",5),"ACCEPTED"),
      (make_intent("MSFT","SELL",8),"PARTIAL"),
      (make_intent("SPY","BUY",3,"limit",500.0),"REJECTED"),
      (make_intent("QQQ","BUY",2),"REJECTED"),
    ]
    rows=[]
    for i,(intent,outcome) in enumerate(cases,1):
        cid=client_order_id(intent);payload=build_payload(intent,cid);ser=serialize_request(payload)
        queue=queue_order(intent,cid);ack=ack_simulator(intent,config)
        response=broker_response(intent,outcome,config);retry=retry_simulation(response,config)
        receipt=submission_receipt(intent,cid,ack,response,retry)
        rows.append({"scenario":i,"intent":intent,"client_order_id":cid,"payload":payload,
                     "serialization":ser,"queue":queue,"ack":ack,"response":response,
                     "retry":retry,"receipt":receipt})
    dup=idempotency_guard([rows[0]["client_order_id"]["client_order_id"]]*2)
    replay=replay_guard([rows[0]["receipt"],rows[0]["receipt"]])
    deterministic=deterministic_replay(rows[0]["intent"],"ACCEPTED",config)
    d={"stage":"V85.76","status":"PASS","scenario_count":len(rows),
       "accepted_count":sum(r["receipt"]["status"]=="SIM_ACCEPTED" for r in rows),
       "partial_count":sum(r["receipt"]["status"]=="SIM_PARTIAL" for r in rows),
       "rejected_count":sum(r["receipt"]["status"]=="SIM_REJECTED" for r in rows),
       "ack_count":sum(r["ack"]["ack_status"]=="ACK_SIMULATED" for r in rows),
       "idempotency_duplicate_detected":dup["duplicate_detected"],
       "replay_detected":replay["replay_detected"],
       "deterministic_replay":deterministic["deterministic"],
       "rows":rows}
    d["scenario_sha256"]=hj(d);return d

def build_audit(config,policy,scenarios,machine):
    checks={"policy_pass":policy["status"]=="PASS",
      "simulation_only":policy["simulation_only"],
      "network_post_false":policy["network_post_enabled"] is False,
      "broker_write_false":policy["broker_write_enabled"] is False,
      "scenario_count_four":scenarios["scenario_count"]==4,
      "ack_count_four":scenarios["ack_count"]==4,
      "accepted_positive":scenarios["accepted_count"]>0,
      "partial_positive":scenarios["partial_count"]>0,
      "rejected_positive":scenarios["rejected_count"]>0,
      "duplicate_detected":scenarios["idempotency_duplicate_detected"],
      "replay_detected":scenarios["replay_detected"],
      "deterministic_replay":scenarios["deterministic_replay"],
      "state_machine_no_network":machine["network_submit_state_present"] is False,
      "state_machine_no_actual":machine["actual_order_state_present"] is False,
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V85.77","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="paper-order-submission-sim-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V85.78","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"paper_order_submission_sim_master_ledger_v85_78.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"paper_order_submission_sim_master_ledger_v85_78.json";b=lp.read_bytes()
    d={"stage":"V85.79","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),
       "sha256":hb(b),"byte_size":len(b)}},"network_requests_executed":0,
       "credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"paper_order_submission_sim_manifest_v85_79.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"paper_order_submission_sim_master_ledger_v85_78.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_authorization_certificate(root/"release/v85_60/output/paper_order_authorization_certificate_v85_60.json")
    policy=submission_policy();scenarios=build_scenarios(c);machine=state_machine()
    audit=build_audit(c,policy,scenarios,machine)
    docs={"policy":policy,"scenarios":scenarios,"state_machine":machine,
          "retry_policy":retry_policy(c),"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"scenario_count":scenarios["scenario_count"],
      "accepted_count":scenarios["accepted_count"],"partial_count":scenarios["partial_count"],
      "rejected_count":scenarios["rejected_count"],"ack_count":scenarios["ack_count"],
      "idempotency_duplicate_detected":scenarios["idempotency_duplicate_detected"],
      "replay_detected":scenarios["replay_detected"],
      "deterministic_replay":scenarios["deterministic_replay"],
      "audit_status":audit["status"],
      "source_paper_authorization_complete":source["paper_order_authorization_complete"]}
    return {"stage":"V85.80","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,
      "trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v85_60_certificate_present":(root/"release/v85_60/output/paper_order_authorization_certificate_v85_60.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","scenario_count_four":s["scenario_count"]==4,
      "ack_count_four":s["ack_count"]==4,"accepted_positive":s["accepted_count"]>0,
      "partial_positive":s["partial_count"]>0,"rejected_positive":s["rejected_count"]>0,
      "duplicate_detected":s["idempotency_duplicate_detected"],
      "replay_detected":s["replay_detected"],"deterministic_replay":s["deterministic_replay"],
      "audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,
      "credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,
      "actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V85.80","status":status,"scope":"PAPER_ORDER_SUBMISSION_SIMULATION_OFFLINE",
      "stages_completed":[f"V85.{i:02d}" for i in range(61,81)],
      "completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"paper_order_submission_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "paper_order_submission_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "paper_order_submission_authorized":False,"live_trading_authorized":False,
      "paper_order_submission_simulation_complete":status=="PASS",
      "next_phase":"V85_81_PAPER_BROKER_NETWORK_ENABLEMENT_FOUNDATION"}
    cert["certificate_sha256"]=hj(cert)
    wj(out/"paper_order_submission_sim_certificate_v85_80.json",cert)
    wj(out/"paper_order_submission_sim_verify_v85_80.json",{"stage":"V85.80",
      "status":status,"verified":not failed,"certificate_sha256":cert["certificate_sha256"],
      "failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
