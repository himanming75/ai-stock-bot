from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2X"
SCHEMA="v75.2x.offline_paper_order_submission_execution.1"
SOURCE_SCHEMA="v75.2w.offline_paper_order_submission_authorization.1"

class OrderSubmissionExecutionError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OrderSubmissionExecutionError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OrderSubmissionExecutionError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OrderSubmissionExecutionError("top-level JSON must be an object")
    return v

def parse_ts(v:Any,name:str)->datetime:
    if not isinstance(v,str) or not v: raise OrderSubmissionExecutionError(f"{name} invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OrderSubmissionExecutionError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None: raise OrderSubmissionExecutionError(f"{name} must include timezone")
    return d

def validate_config(c:Dict[str,Any])->None:
    if c.get("execution_scope")!="OFFLINE_PAPER_ORDER_SUBMISSION_STATE_TRANSITION_ONLY":
        raise OrderSubmissionExecutionError("execution_scope invalid")
    if c.get("submitted_order_state")!="SUBMITTED_OFFLINE_REFERENCE":
        raise OrderSubmissionExecutionError("submitted_order_state invalid")
    for k in ("require_authorization_integrity","require_manifest_integrity",
              "require_single_use_token","require_token_unconsumed",
              "require_token_unexpired","prevent_output_overwrite"):
        if c.get(k) is not True: raise OrderSubmissionExecutionError(f"{k} must be true")
    for k in ("broker_routing_allowed","fill_simulation_allowed","paper_broker_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed",
              "external_side_effects_allowed"):
        if c.get(k) is not False: raise OrderSubmissionExecutionError(f"{k} must be false")

def validate_source(s:Dict[str,Any],when:datetime)->None:
    if s.get("status")!="PASS": raise OrderSubmissionExecutionError("authorization status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise OrderSubmissionExecutionError("unsupported authorization schema")
    if s.get("authorization_state")!="AUTHORIZED_NOT_EXECUTED":
        raise OrderSubmissionExecutionError("authorization not executable")
    if s.get("authorization_scope")!="OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY":
        raise OrderSubmissionExecutionError("authorization scope invalid")
    if s.get("order_submission_authorized") is not True or s.get("order_submission_executed") is not False:
        raise OrderSubmissionExecutionError("submission authorization state invalid")
    if s.get("submission_execution_allowed") is not True or s.get("token_consumed") is not False:
        raise OrderSubmissionExecutionError("submission execution not allowed")

    observed=s.get("offline_paper_order_submission_authorization_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_order_submission_authorization_sha256",None)
    if observed!=sha256_of(clone): raise OrderSubmissionExecutionError("authorization integrity failed")
    for field,h in (("authorized_order_manifest","authorized_order_manifest_sha256"),
                    ("authorization_token","authorization_token_sha256"),
                    ("authorization_checks","authorization_checks_sha256"),
                    ("authorization_ledger","authorization_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(field)): raise OrderSubmissionExecutionError(f"{field} integrity failed")

    gate=s.get("authorization_gate",{})
    expected={"order_submission_authorized":True,"submission_execution_allowed":True,
              "order_submission_allowed":False,"broker_routing_allowed":False,
              "fill_simulation_allowed":False,"paper_broker_allowed":False,
              "live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OrderSubmissionExecutionError(f"authorization_gate {k} invalid")

    token=s.get("authorization_token")
    if not isinstance(token,dict): raise OrderSubmissionExecutionError("authorization token required")
    material={k:token.get(k) for k in ("authorization_id","validation_id","issued_at",
            "expires_at","nonce","scope","authorized_paper_order_ids")}
    if token.get("token_sha256")!=sha256_of(material): raise OrderSubmissionExecutionError("token integrity failed")
    if token.get("single_use") is not True or token.get("consumed") is not False:
        raise OrderSubmissionExecutionError("token single-use state invalid")
    if token.get("token_state")!="ISSUED_NOT_CONSUMED" or token.get("consumed_at") is not None:
        raise OrderSubmissionExecutionError("token state invalid")
    issued=parse_ts(token.get("issued_at"),"issued_at")
    expires=parse_ts(token.get("expires_at"),"expires_at")
    if when<issued: raise OrderSubmissionExecutionError("execution before token issuance")
    if when>expires: raise OrderSubmissionExecutionError("authorization token expired")
    if token.get("authorization_id")!=s.get("authorization_id"):
        raise OrderSubmissionExecutionError("token authorization identity mismatch")
    if token.get("validation_id")!=s.get("validation_id"):
        raise OrderSubmissionExecutionError("token validation identity mismatch")
    if token.get("scope")!=s.get("authorization_scope"):
        raise OrderSubmissionExecutionError("token scope mismatch")

    manifest=s.get("authorized_order_manifest")
    if not isinstance(manifest,list) or not manifest:
        raise OrderSubmissionExecutionError("authorized order manifest required")
    if s.get("authorized_order_count")!=len(manifest):
        raise OrderSubmissionExecutionError("authorized order count mismatch")
    ids=[o.get("paper_order_id") for o in manifest]
    if token.get("authorized_paper_order_ids")!=ids:
        raise OrderSubmissionExecutionError("token paper-order lock mismatch")
    if len(ids)!=len(set(ids)): raise OrderSubmissionExecutionError("duplicate paper order id")
    for o in manifest:
        if o.get("submission_execution_authorized") is not True:
            raise OrderSubmissionExecutionError("submission execution not authorized")
        if o.get("order_state")!="CREATED_NOT_SUBMITTED":
            raise OrderSubmissionExecutionError("source order state invalid")
        for k in ("submitted","broker_routed","filled"):
            if o.get(k) is not False: raise OrderSubmissionExecutionError(f"unsafe source order state: {k}")

    for k in ("broker_routing_allowed","fill_simulation_allowed","paper_broker_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise OrderSubmissionExecutionError(f"{k} must be false")
    if s.get("orders_submitted")!=0 or s.get("fills_created")!=0:
        raise OrderSubmissionExecutionError("external submission or fill side effect detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise OrderSubmissionExecutionError("safety violation")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise OrderSubmissionExecutionError("safety lock invalid")

def build_execution(source:Dict[str,Any],config:Dict[str,Any],executed_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    when=datetime.now(timezone.utc).replace(microsecond=0) if executed_at is None else parse_ts(executed_at,"executed_at")
    validate_source(source,when)
    ts=when.isoformat()
    eid="OSE-"+hashlib.sha256(f"{source['authorization_id']}|{ts}|{VERSION}".encode()).hexdigest()[:16].upper()

    submitted=[]
    for o in source["authorized_order_manifest"]:
        submitted.append({
            "offline_submission_id":"OSUB-"+hashlib.sha256(
                f"{eid}|{o['paper_order_id']}|{ts}".encode()).hexdigest()[:16].upper(),
            "paper_order_id":o["paper_order_id"],"order_intent_id":o["order_intent_id"],
            "authorization_id":source["authorization_id"],
            "symbol":o["symbol"],"side":o["side"],"quantity":o["quantity"],
            "order_type":o["order_type"],"time_in_force":o["time_in_force"],
            "reference_price":o["reference_price"],
            "previous_order_state":"CREATED_NOT_SUBMITTED",
            "order_state":config["submitted_order_state"],
            "submitted_offline":True,"submitted_at":ts,
            "external_submission":False,"broker_routed":False,
            "network_used":False,"filled":False,"fill_simulated":False,
            "external_side_effects":False
        })

    token=copy.deepcopy(source["authorization_token"])
    token.update({"consumed":True,"consumed_at":ts,"token_state":"CONSUMED"})

    package={"submission_execution_id":eid,"authorization_id":source["authorization_id"],
             "validation_id":source["validation_id"],"execution_id":source["execution_id"],
             "session_id":source["session_id"],"cycle_id":source["cycle_id"],
             "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
             "executed_at":ts,"immutable":True,"offline_only":True,
             "submitted_order_count":len(submitted),"submitted_orders":submitted,
             "external_orders_submitted":0,"broker_routes_created":0,
             "fills_created":0,"network_source":False}
    checks=[
      {"check_index":1,"check":"ORDER_SUBMISSION_AUTHORIZATION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"SUBMISSION_TOKEN_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"SUBMISSION_TOKEN_TIME_WINDOW","state":"PASS"},
      {"check_index":4,"check":"SUBMISSION_TOKEN_SINGLE_USE","state":"CONSUMED"},
      {"check_index":5,"check":"PAPER_ORDER_IDENTITIES_LOCKED","state":"LOCKED"},
      {"check_index":6,"check":"OFFLINE_SUBMISSION_STATE_TRANSITION","state":"PASS"},
      {"check_index":7,"check":"EXTERNAL_ORDER_SUBMISSION_BLOCKED","state":"PASS"},
      {"check_index":8,"check":"BROKER_ROUTING_NOT_STARTED","state":"PASS"},
      {"check_index":9,"check":"FILL_SIMULATION_NOT_STARTED","state":"PASS"},
      {"check_index":10,"check":"ZERO_EXTERNAL_SIDE_EFFECTS","state":"PASS"},
      {"check_index":11,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    ledger=[
      {"ledger_index":1,"event":"ORDER_SUBMISSION_AUTHORIZATION_VERIFIED","state":"PASS","execution_id":eid},
      {"ledger_index":2,"event":"SINGLE_USE_SUBMISSION_TOKEN_CONSUMED","state":"CONSUMED","execution_id":eid},
      {"ledger_index":3,"event":"PAPER_ORDER_IDENTITIES_LOCKED","state":"LOCKED","execution_id":eid},
      {"ledger_index":4,"event":"OFFLINE_SUBMISSION_STATE_RECORDED","state":"PASS","execution_id":eid},
      {"ledger_index":5,"event":"EXTERNAL_ROUTING_AND_FILL_BLOCKED","state":"ENFORCED","execution_id":eid},
      {"ledger_index":6,"event":"ORDER_SUBMISSION_EXECUTION_COMPLETED","state":"READY_FOR_SUBMISSION_VALIDATION","execution_id":eid}]
    out={"status":"PASS","decision":"offline_paper_order_submission_executed",
         "submission_execution_id":eid,"execution_state":"READY_FOR_SUBMISSION_VALIDATION",
         "authorization_id":source["authorization_id"],"authorization_state":"CONSUMED",
         "order_submission_authorized":True,"order_submission_executed":True,
         "token_consumed":True,"consumed_authorization_token":token,
         "consumed_authorization_token_sha256":sha256_of(token),
         "offline_submission_package":package,
         "offline_submission_package_sha256":sha256_of(package),
         "execution_checks":checks,"execution_checks_sha256":sha256_of(checks),
         "execution_ledger":ledger,"execution_ledger_sha256":sha256_of(ledger),
         "offline_submissions_recorded":len(submitted),
         "external_orders_submitted":0,"broker_routes_created":0,"fills_created":0,
         "execution_gate":{"offline_submission_recorded":True,
            "submission_validation_allowed":True,"external_order_submission_allowed":False,
            "broker_routing_allowed":False,"fill_simulation_allowed":False,
            "paper_broker_allowed":False,"live_orders_allowed":False,
            "network_allowed":False,"next_version":"75.2Y"},
         "source_order_submission_authorization_sha256":source["offline_paper_order_submission_authorization_sha256"],
         "source_order_object_validation_sha256":source["source_order_object_validation_sha256"],
         "source_order_generation_execution_sha256":source["source_order_generation_execution_sha256"],
         "validation_id":source["validation_id"],"execution_id":source["execution_id"],
         "authorization_source_id":source["authorization_source_id"],
         "session_id":source["session_id"],"cycle_id":source["cycle_id"],
         "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
         "external_order_submission_allowed":False,"broker_routing_allowed":False,
         "fill_simulation_allowed":False,"paper_broker_allowed":False,
         "live_orders_allowed":False,"network_allowed":False,
         "broker_connection_allowed":False,"approved_for_live":False,"network_used":False,
         "safety_lock":copy.deepcopy(source["safety_lock"]),
         "executed_at":ts,"schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_order_submission_execution_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path,prevent:bool=True)->None:
    d.mkdir(parents=True,exist_ok=True)
    primary=d/"offline_paper_order_submission_execution_v75_2x.json"
    if prevent and primary.exists():
        raise OrderSubmissionExecutionError(f"execution output already exists: {primary}")
    payloads={
      "offline_paper_order_submission_execution_v75_2x.json":out,
      "offline_paper_submitted_orders_v75_2x.json":out["offline_submission_package"],
      "offline_paper_order_submission_consumed_token_v75_2x.json":out["consumed_authorization_token"],
      "offline_paper_order_submission_execution_checks_v75_2x.json":{"submission_execution_id":out["submission_execution_id"],"execution_checks":out["execution_checks"],"execution_checks_sha256":out["execution_checks_sha256"]},
      "offline_paper_order_submission_execution_ledger_v75_2x.json":{"submission_execution_id":out["submission_execution_id"],"execution_ledger":out["execution_ledger"],"execution_ledger_sha256":out["execution_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_order_submission_execution_v75_2x.sha256").write_text(
        out["offline_paper_order_submission_execution_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--authorization",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--executed-at")
    a=p.parse_args(argv)
    try:
        c=read_json(Path(a.config))
        out=build_execution(read_json(Path(a.authorization)),c,a.executed_at)
        write_outputs(out,Path(a.output_dir),c.get("prevent_output_overwrite",True))
        first=out["offline_submission_package"]["submitted_orders"][0]
        print(json.dumps({"status":out["status"],"decision":out["decision"],
          "submission_execution_id":out["submission_execution_id"],
          "execution_state":out["execution_state"],"authorization_state":out["authorization_state"],
          "offline_submissions_recorded":out["offline_submissions_recorded"],
          "first_submitted_order":first,"token_consumed":True,
          "submission_validation_allowed":True,
          "external_order_submission_allowed":False,"external_orders_submitted":0,
          "broker_routing_allowed":False,"broker_routes_created":0,
          "fill_simulation_allowed":False,"fills_created":0,
          "paper_broker_allowed":False,"network_allowed":False,
          "approved_for_live":False,"network_used":False,
          "offline_paper_order_submission_execution_sha256":out["offline_paper_order_submission_execution_sha256"]},indent=2,sort_keys=True))
        return 0
    except (OrderSubmissionExecutionError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_order_submission_execution_failed",
          "error":str(e),"approved_for_live":False,"network_used":False,
          "external_orders_submitted":0,"broker_routes_created":0,"fills_created":0,
          "version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
