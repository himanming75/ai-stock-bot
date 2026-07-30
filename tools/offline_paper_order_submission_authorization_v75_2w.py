from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2W"
SCHEMA="v75.2w.offline_paper_order_submission_authorization.1"
SOURCE_SCHEMA="v75.2v.offline_paper_order_object_validation.1"

class OrderSubmissionAuthorizationError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OrderSubmissionAuthorizationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OrderSubmissionAuthorizationError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OrderSubmissionAuthorizationError("top-level JSON must be an object")
    return v

def parse_ts(v:Any,name:str)->datetime:
    if not isinstance(v,str) or not v: raise OrderSubmissionAuthorizationError(f"{name} invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OrderSubmissionAuthorizationError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None: raise OrderSubmissionAuthorizationError(f"{name} must include timezone")
    return d

def validate_config(c:Dict[str,Any])->None:
    if c.get("authorization_scope")!="OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY":
        raise OrderSubmissionAuthorizationError("authorization_scope invalid")
    ttl=c.get("authorization_ttl_seconds")
    if isinstance(ttl,bool) or not isinstance(ttl,int) or ttl<60 or ttl>3600:
        raise OrderSubmissionAuthorizationError("authorization_ttl_seconds must be 60..3600")
    for k in ("require_validation_integrity","require_validated_orders_integrity",
              "require_zero_submissions","require_zero_fills","require_single_use_token"):
        if c.get(k) is not True: raise OrderSubmissionAuthorizationError(f"{k} must be true")
    for k in ("order_submission_allowed","broker_routing_allowed","fill_simulation_allowed",
              "paper_broker_allowed","live_orders_allowed","network_allowed",
              "broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False: raise OrderSubmissionAuthorizationError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS": raise OrderSubmissionAuthorizationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise OrderSubmissionAuthorizationError("unsupported source schema")
    if s.get("validation_state")!="READY_FOR_ORDER_SUBMISSION_AUTHORIZATION":
        raise OrderSubmissionAuthorizationError("source not ready for submission authorization")
    if s.get("order_objects_validated") is not True:
        raise OrderSubmissionAuthorizationError("order objects not validated")
    observed=s.get("offline_paper_order_object_validation_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_order_object_validation_sha256",None)
    if observed!=sha256_of(clone): raise OrderSubmissionAuthorizationError("validation integrity failed")
    for field,h in (("validated_orders","validated_orders_sha256"),
                    ("validation_checks","validation_checks_sha256"),
                    ("validation_ledger","validation_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(field)): raise OrderSubmissionAuthorizationError(f"{field} integrity failed")
    gate=s.get("validation_gate",{})
    expected={"order_objects_validated":True,"order_submission_authorization_allowed":True,
              "order_submission_allowed":False,"fill_simulation_allowed":False,
              "paper_broker_allowed":False,"live_orders_allowed":False,
              "network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OrderSubmissionAuthorizationError(f"validation_gate {k} invalid")
    orders=s.get("validated_orders")
    if not isinstance(orders,list) or not orders: raise OrderSubmissionAuthorizationError("validated orders required")
    if s.get("validated_order_count")!=len(orders): raise OrderSubmissionAuthorizationError("validated order count mismatch")
    ids=set()
    for o in orders:
        oid=o.get("paper_order_id")
        if not isinstance(oid,str) or oid in ids: raise OrderSubmissionAuthorizationError("duplicate or invalid paper order id")
        ids.add(oid)
        if o.get("validation_state")!="PASS": raise OrderSubmissionAuthorizationError("order validation state invalid")
        if o.get("order_state")!="CREATED_NOT_SUBMITTED": raise OrderSubmissionAuthorizationError("order state invalid")
        for k in ("submitted","filled","fill_simulated","broker_routed","network_used"):
            if o.get(k) is not False: raise OrderSubmissionAuthorizationError(f"unsafe validated order state: {k}")
    for k in ("order_submission_allowed","fill_simulation_allowed","paper_broker_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise OrderSubmissionAuthorizationError(f"{k} must be false")
    if s.get("orders_submitted")!=0 or s.get("fills_created")!=0:
        raise OrderSubmissionAuthorizationError("submission or fill side effect detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise OrderSubmissionAuthorizationError("safety violation")
    lock=s.get("safety_lock",{})
    if lock.get("lock_state")!="ENFORCED": raise OrderSubmissionAuthorizationError("safety lock invalid")
    return orders

def build_authorization(source:Dict[str,Any],config:Dict[str,Any],issued_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    orders=validate_source(source)
    when=datetime.now(timezone.utc).replace(microsecond=0) if issued_at is None else parse_ts(issued_at,"issued_at")
    expires=when+timedelta(seconds=config["authorization_ttl_seconds"])
    issued=when.isoformat(); expiry=expires.isoformat()
    auth_id="OSA-"+hashlib.sha256(f"{source['validation_id']}|{source['validated_orders_sha256']}|{issued}|{VERSION}".encode()).hexdigest()[:16].upper()
    nonce=hashlib.sha256(f"{auth_id}|{expiry}|nonce".encode()).hexdigest()[:32]
    order_ids=[o["paper_order_id"] for o in orders]
    token_material={"authorization_id":auth_id,"validation_id":source["validation_id"],
                    "issued_at":issued,"expires_at":expiry,"nonce":nonce,
                    "scope":"OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY",
                    "authorized_paper_order_ids":order_ids}
    token={**token_material,"token_sha256":sha256_of(token_material),
           "single_use":True,"consumed":False,"consumed_at":None,
           "token_state":"ISSUED_NOT_CONSUMED"}
    manifest=[{"paper_order_id":o["paper_order_id"],"order_intent_id":o["order_intent_id"],
               "symbol":o["symbol"],"side":o["side"],"quantity":o["quantity"],
               "order_type":o["order_type"],"time_in_force":o["time_in_force"],
               "reference_price":o["reference_price"],"order_state":o["order_state"],
               "submission_execution_authorized":True,"submitted":False,
               "broker_routed":False,"filled":False} for o in orders]
    checks=[
      {"check_index":1,"check":"ORDER_OBJECT_VALIDATION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"VALIDATED_ORDER_MANIFEST_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"PAPER_ORDER_IDENTITIES_LOCKED","state":"LOCKED"},
      {"check_index":4,"check":"ORDER_SUBMISSION_NOT_STARTED","state":"PASS"},
      {"check_index":5,"check":"BROKER_ROUTING_NOT_STARTED","state":"PASS"},
      {"check_index":6,"check":"FILL_SIMULATION_NOT_STARTED","state":"PASS"},
      {"check_index":7,"check":"ZERO_EXTERNAL_SIDE_EFFECTS","state":"PASS"},
      {"check_index":8,"check":"SINGLE_USE_TOKEN_POLICY","state":"ENFORCED"},
      {"check_index":9,"check":"AUTHORIZATION_SCOPE_LIMIT","state":"ENFORCED"},
      {"check_index":10,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":11,"check":"BROKER_DISCONNECTED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    ledger=[
      {"ledger_index":1,"event":"ORDER_OBJECT_VALIDATION_VERIFIED","state":"PASS","authorization_id":auth_id},
      {"ledger_index":2,"event":"PAPER_ORDER_IDENTITIES_LOCKED","state":"LOCKED","authorization_id":auth_id},
      {"ledger_index":3,"event":"OFFLINE_SUBMISSION_EXECUTION_SCOPE_AUTHORIZED","state":"AUTHORIZED","authorization_id":auth_id},
      {"ledger_index":4,"event":"SINGLE_USE_TOKEN_ISSUED","state":"ISSUED_NOT_CONSUMED","authorization_id":auth_id},
      {"ledger_index":5,"event":"SUBMISSION_ROUTING_AND_FILL_REMAIN_BLOCKED","state":"ENFORCED","authorization_id":auth_id},
      {"ledger_index":6,"event":"ORDER_SUBMISSION_AUTHORIZATION_COMPLETED","state":"AUTHORIZED_NOT_EXECUTED","authorization_id":auth_id}]
    out={"status":"PASS","decision":"offline_paper_order_submission_authorized",
         "authorization_id":auth_id,"authorization_scope":"OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY",
         "authorization_state":"AUTHORIZED_NOT_EXECUTED",
         "order_submission_authorized":True,"order_submission_executed":False,
         "submission_execution_allowed":True,"order_submission_allowed":False,
         "authorized_order_count":len(manifest),"authorized_order_manifest":manifest,
         "authorized_order_manifest_sha256":sha256_of(manifest),
         "authorization_token":token,"authorization_token_sha256":sha256_of(token),
         "authorization_checks":checks,"authorization_checks_sha256":sha256_of(checks),
         "authorization_ledger":ledger,"authorization_ledger_sha256":sha256_of(ledger),
         "authorization_gate":{"order_submission_authorized":True,
            "submission_execution_allowed":True,"order_submission_allowed":False,
            "broker_routing_allowed":False,"fill_simulation_allowed":False,
            "paper_broker_allowed":False,"live_orders_allowed":False,
            "network_allowed":False,"next_version":"75.2X"},
         "source_order_object_validation_sha256":source["offline_paper_order_object_validation_sha256"],
         "source_validated_orders_sha256":source["validated_orders_sha256"],
         "source_order_generation_execution_sha256":source["source_order_generation_execution_sha256"],
         "validation_id":source["validation_id"],"execution_id":source["execution_id"],
         "authorization_source_id":source["authorization_id"],
         "session_id":source["session_id"],"cycle_id":source["cycle_id"],
         "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
         "issued_at":issued,"expires_at":expiry,
         "token_consumed":False,"orders_submitted":0,"fills_created":0,
         "broker_routing_allowed":False,"fill_simulation_allowed":False,
         "paper_broker_allowed":False,"live_orders_allowed":False,
         "network_allowed":False,"broker_connection_allowed":False,
         "approved_for_live":False,"network_used":False,
         "safety_lock":copy.deepcopy(source["safety_lock"]),
         "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_order_submission_authorization_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_order_submission_authorization_v75_2w.json":out,
      "offline_paper_order_submission_authorization_token_v75_2w.json":out["authorization_token"],
      "offline_paper_authorized_submission_orders_v75_2w.json":{"authorization_id":out["authorization_id"],"authorized_order_manifest":out["authorized_order_manifest"],"authorized_order_manifest_sha256":out["authorized_order_manifest_sha256"]},
      "offline_paper_order_submission_authorization_checks_v75_2w.json":{"authorization_id":out["authorization_id"],"authorization_checks":out["authorization_checks"],"authorization_checks_sha256":out["authorization_checks_sha256"]},
      "offline_paper_order_submission_authorization_ledger_v75_2w.json":{"authorization_id":out["authorization_id"],"authorization_ledger":out["authorization_ledger"],"authorization_ledger_sha256":out["authorization_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_order_submission_authorization_v75_2w.sha256").write_text(out["offline_paper_order_submission_authorization_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--issued-at")
    a=p.parse_args(argv)
    try:
        out=build_authorization(read_json(Path(a.input)),read_json(Path(a.config)),a.issued_at)
        write_outputs(out,Path(a.output_dir))
        print(json.dumps({"status":out["status"],"decision":out["decision"],
          "authorization_id":out["authorization_id"],"authorization_scope":out["authorization_scope"],
          "authorization_state":out["authorization_state"],
          "authorized_order_count":out["authorized_order_count"],
          "first_authorized_order":out["authorized_order_manifest"][0],
          "expires_at":out["expires_at"],"token_state":out["authorization_token"]["token_state"],
          "token_consumed":False,"submission_execution_allowed":True,
          "order_submission_allowed":False,"orders_submitted":0,
          "broker_routing_allowed":False,"fill_simulation_allowed":False,
          "fills_created":0,"paper_broker_allowed":False,"network_allowed":False,
          "approved_for_live":False,"network_used":False,
          "offline_paper_order_submission_authorization_sha256":out["offline_paper_order_submission_authorization_sha256"]},indent=2,sort_keys=True))
        return 0
    except (OrderSubmissionAuthorizationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_order_submission_authorization_failed",
          "error":str(e),"approved_for_live":False,"network_used":False,
          "orders_submitted":0,"fills_created":0,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
