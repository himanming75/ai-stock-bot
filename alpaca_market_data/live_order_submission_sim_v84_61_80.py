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
class LiveOrderSubmissionSimulationConfig:
    mode:str="LIVE_ORDER_SUBMISSION_SIMULATION_OFFLINE"
    environment:str="LIVE"
    retry_limit:int=3
    partial_fill_ratio:float=0.5
    ack_latency_ms:int=25
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="LIVE_ORDER_SUBMISSION_SIMULATION_OFFLINE": raise ValueError("safe mode")
        if self.environment!="LIVE": raise ValueError("live environment")
        if self.retry_limit<0 or not 0<self.partial_fill_ratio<1 or self.ack_latency_ms<0:
            raise ValueError("simulation config")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline submission simulation only")

def validate_authorization_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V84.60" or c.get("status")!="PASS":
        raise ValueError("bad V84.60 certificate")
    if c.get("live_order_authorization_foundation_complete") is not True:
        raise ValueError("authorization prerequisite")
    if c.get("live_order_submission_authorized") is not False or c.get("actual_orders_submitted")!=0:
        raise ValueError("unsafe prerequisite")
    return c

def submission_policy():
    d={"stage":"V84.61","status":"PASS","environment":"LIVE","simulation_only":True,
       "network_submission_enabled":False,"broker_write_enabled":False,
       "live_order_submission_authorized":False}
    d["policy_sha256"]=hj(d);return d

def make_submission_intent(symbol,side,quantity,reference_price,authorization_ready=True):
    side=side.upper();symbol=symbol.upper()
    if side not in {"BUY","SELL"} or quantity<1 or reference_price<=0:
        raise ValueError("intent")
    d={"stage":"V84.62","submission_intent_id":"live-submit-"+hj([symbol,side,quantity,reference_price])[:20],
       "symbol":symbol,"side":side,"quantity":quantity,"reference_price":float(reference_price),
       "authorization_ready":authorization_ready,"actual_submission_authorized":False}
    d["intent_sha256"]=hj(d);return d

def idempotency_contract(intent):
    d={"stage":"V84.63","submission_intent_id":intent["submission_intent_id"],
       "idempotency_key":"live-submit-idem-"+hj(intent)[:24]}
    d["idempotency_sha256"]=hj(d);return d

def queue_submission(intent,idem):
    status="QUEUED_FOR_SIMULATION" if intent["authorization_ready"] else "REJECTED_AUTHORIZATION"
    d={"stage":"V84.64","queue_id":"live-submit-queue-"+hj([intent,idem])[:20],
       "submission_intent_id":intent["submission_intent_id"],"idempotency_key":idem["idempotency_key"],
       "queue_status":status,"network_delivery_allowed":False}
    d["queue_sha256"]=hj(d);return d

def duplicate_guard(keys):
    duplicate=len(keys)!=len(set(keys))
    d={"stage":"V84.65","key_count":len(keys),"duplicate_detected":duplicate,"accepted":not duplicate}
    d["duplicate_sha256"]=hj(d);return d

def serialize_payload(intent):
    d={"stage":"V84.66","payload":{"symbol":intent["symbol"],"side":intent["side"],
       "qty":intent["quantity"],"type":"market","time_in_force":"day"},
       "simulation_payload":True,"network_ready":False}
    d["payload_sha256"]=hj(d);return d

def ack_simulator(intent,config):
    d={"stage":"V84.67","ack_id":"live-ack-"+hj(intent)[:20],"ack_status":"ACK_SIMULATED",
       "latency_ms":config.ack_latency_ms,"network_ack":False,"actual_broker_ack":False}
    d["ack_sha256"]=hj(d);return d

def broker_response_simulator(intent,outcome,config):
    outcome=outcome.upper()
    if outcome not in {"ACCEPTED","REJECTED","PARTIAL"}: raise ValueError("outcome")
    filled=0
    if outcome=="ACCEPTED": filled=intent["quantity"]
    elif outcome=="PARTIAL": filled=max(1,int(intent["quantity"]*config.partial_fill_ratio))
    d={"stage":"V84.68","simulated_order_id":"live-sim-order-"+hj([intent,outcome])[:20],
       "outcome":outcome,"requested_quantity":intent["quantity"],"filled_quantity":filled,
       "remaining_quantity":intent["quantity"]-filled,"network_response":False,
       "actual_broker_order":False}
    d["response_sha256"]=hj(d);return d

def retry_policy(config):
    d={"stage":"V84.69","retry_limit":config.retry_limit,
       "backoff_seconds":[2**i for i in range(config.retry_limit)],
       "simulation_retry_enabled":True,"network_retry_enabled":False}
    d["retry_policy_sha256"]=hj(d);return d

def retry_simulation(response,config):
    retryable=response["outcome"]=="REJECTED"
    d={"stage":"V84.70","response_outcome":response["outcome"],"retryable":retryable,
       "simulated_retry_attempts":config.retry_limit if retryable else 0,
       "network_retry_attempts":0}
    d["retry_sha256"]=hj(d);return d

def submission_receipt(intent,queue,ack,response,retry):
    status_map={"ACCEPTED":"SIM_ACCEPTED","REJECTED":"SIM_REJECTED","PARTIAL":"SIM_PARTIAL"}
    d={"stage":"V84.71","receipt_id":"live-submit-receipt-"+hj([intent,queue,ack,response])[:24],
       "status":status_map[response["outcome"]],"ack_status":ack["ack_status"],
       "queue_status":queue["queue_status"],"filled_quantity":response["filled_quantity"],
       "remaining_quantity":response["remaining_quantity"],
       "simulated_retry_attempts":retry["simulated_retry_attempts"],
       "actual_order_submitted":False,"live_order_submission_authorized":False}
    d["receipt_sha256"]=hj(d);return d

def replay_guard(receipts):
    hashes=[x["receipt_sha256"] for x in receipts]
    duplicate=len(hashes)!=len(set(hashes))
    d={"stage":"V84.72","receipt_count":len(receipts),"replay_detected":duplicate,"accepted":not duplicate}
    d["replay_sha256"]=hj(d);return d

def deterministic_replay(intent,outcome,config):
    def one():
        idem=idempotency_contract(intent);q=queue_submission(intent,idem);p=serialize_payload(intent)
        ack=ack_simulator(intent,config);r=broker_response_simulator(intent,outcome,config)
        rt=retry_simulation(r,config);rc=submission_receipt(intent,q,ack,r,rt)
        return {"idempotency":idem,"queue":q,"payload":p,"ack":ack,"response":r,"retry":rt,"receipt":rc}
    a=one();b=one()
    d={"stage":"V84.73","deterministic":a==b,"receipt_sha256":a["receipt"]["receipt_sha256"]}
    d["determinism_sha256"]=hj(d);return d

def build_scenarios(config):
    cases=[
      (make_submission_intent("AAPL","BUY",10,100), "ACCEPTED"),
      (make_submission_intent("MSFT","SELL",8,200), "PARTIAL"),
      (make_submission_intent("SPY","BUY",5,500), "REJECTED"),
      (make_submission_intent("QQQ","BUY",4,400,authorization_ready=False), "REJECTED"),
    ]
    rows=[]
    for i,(intent,outcome) in enumerate(cases,1):
        idem=idempotency_contract(intent);q=queue_submission(intent,idem);payload=serialize_payload(intent)
        ack=ack_simulator(intent,config);response=broker_response_simulator(intent,outcome,config)
        retry=retry_simulation(response,config);receipt=submission_receipt(intent,q,ack,response,retry)
        rows.append({"scenario":i,"intent":intent,"idempotency":idem,"queue":q,"payload":payload,
                     "ack":ack,"response":response,"retry":retry,"receipt":receipt})
    dup=duplicate_guard([rows[0]["idempotency"]["idempotency_key"]]*2)
    replay=replay_guard([rows[0]["receipt"],rows[0]["receipt"]])
    deterministic=deterministic_replay(rows[0]["intent"],"ACCEPTED",config)
    d={"stage":"V84.74","status":"PASS","scenario_count":len(rows),
       "accepted_count":sum(x["receipt"]["status"]=="SIM_ACCEPTED" for x in rows),
       "rejected_count":sum(x["receipt"]["status"]=="SIM_REJECTED" for x in rows),
       "partial_count":sum(x["receipt"]["status"]=="SIM_PARTIAL" for x in rows),
       "ack_count":sum(x["ack"]["ack_status"]=="ACK_SIMULATED" for x in rows),
       "authorization_reject_count":sum(x["queue"]["queue_status"]=="REJECTED_AUTHORIZATION" for x in rows),
       "duplicate_detected":dup["duplicate_detected"],"replay_detected":replay["replay_detected"],
       "deterministic_replay":deterministic["deterministic"],"rows":rows}
    d["scenario_sha256"]=hj(d);return d

def state_machine():
    transitions={"CREATED":["QUEUED","REJECTED_AUTHORIZATION"],"QUEUED":["ACK_SIMULATED"],
      "ACK_SIMULATED":["SIM_ACCEPTED","SIM_REJECTED","SIM_PARTIAL"],
      "SIM_PARTIAL":["SIM_COMPLETED","SIM_CANCELED"],"SIM_ACCEPTED":[],"SIM_REJECTED":[],
      "SIM_COMPLETED":[],"SIM_CANCELED":[]}
    d={"stage":"V84.75","initial_state":"CREATED","transitions":transitions,
       "network_submit_state_present":False,"live_submit_state_present":False}
    d["state_machine_sha256"]=hj(d);return d

def build_audit(config,policy,retry,scenarios,machine):
    checks={"policy_pass":policy["status"]=="PASS","simulation_only":policy["simulation_only"],
      "network_submission_false":policy["network_submission_enabled"] is False,
      "broker_write_false":policy["broker_write_enabled"] is False,
      "retry_network_false":retry["network_retry_enabled"] is False,
      "scenario_count_four":scenarios["scenario_count"]==4,"ack_count_four":scenarios["ack_count"]==4,
      "accepted_positive":scenarios["accepted_count"]>0,"rejected_positive":scenarios["rejected_count"]>0,
      "partial_positive":scenarios["partial_count"]>0,
      "authorization_reject_positive":scenarios["authorization_reject_count"]>0,
      "duplicate_detected":scenarios["duplicate_detected"],"replay_detected":scenarios["replay_detected"],
      "deterministic_replay":scenarios["deterministic_replay"],
      "state_machine_no_network":machine["network_submit_state_present"] is False,
      "state_machine_no_live":machine["live_submit_state_present"] is False,
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V84.76","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="live-order-submission-sim-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V84.77","status":"PASS","package_id":pid,"document_count":len(docs),
            "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"live_order_submission_sim_master_ledger_v84_77.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"live_order_submission_sim_master_ledger_v84_77.json";b=lp.read_bytes()
    d={"stage":"V84.78","status":"PASS","package_id":ledger["package_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"live_order_submission_sim_manifest_v84_78.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"live_order_submission_sim_master_ledger_v84_77.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_authorization_certificate(root/"release/v84_60/output/live_order_authorization_certificate_v84_60.json")
    policy=submission_policy();retry=retry_policy(c);scenarios=build_scenarios(c);machine=state_machine()
    audit=build_audit(c,policy,retry,scenarios,machine)
    docs={"submission_policy":policy,"retry_policy":retry,"scenarios":scenarios,"state_machine":machine,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"scenario_count":scenarios["scenario_count"],"accepted_count":scenarios["accepted_count"],
      "rejected_count":scenarios["rejected_count"],"partial_count":scenarios["partial_count"],
      "ack_count":scenarios["ack_count"],"authorization_reject_count":scenarios["authorization_reject_count"],
      "duplicate_detected":scenarios["duplicate_detected"],"replay_detected":scenarios["replay_detected"],
      "deterministic_replay":scenarios["deterministic_replay"],"audit_status":audit["status"],
      "source_live_authorization_complete":source["live_order_authorization_foundation_complete"]}
    return {"stage":"V84.79","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v84_60_certificate_present":(root/"release/v84_60/output/live_order_authorization_certificate_v84_60.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","scenario_count_four":s["scenario_count"]==4,
      "ack_count_four":s["ack_count"]==4,"accepted_positive":s["accepted_count"]>0,
      "rejected_positive":s["rejected_count"]>0,"partial_positive":s["partial_count"]>0,
      "authorization_reject_positive":s["authorization_reject_count"]>0,
      "duplicate_detected":s["duplicate_detected"],"replay_detected":s["replay_detected"],
      "deterministic_replay":s["deterministic_replay"],"audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V84.80","status":status,"scope":"OFFLINE_LIVE_ORDER_SUBMISSION_SIMULATION",
      "stages_completed":[f"V84.{i:02d}" for i in range(61,81)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"live_order_submission_summary":{**s,"package_id":r["package_id"],
        "package_created":r["created"],"package_reused":r["reused"]},
      "live_order_submission_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
      "trading_client_created":False,"actual_orders_submitted":0,
      "live_order_submission_authorized":False,"live_trading_authorized":False,
      "live_order_submission_simulation_complete":status=="PASS",
      "next_phase":"V84_81_LIVE_BROKER_FINAL_CERTIFICATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"live_order_submission_sim_certificate_v84_80.json",cert)
    wj(out/"live_order_submission_sim_verify_v84_80.json",{"stage":"V84.80","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
