from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2U"
SCHEMA="v75.2u.offline_paper_order_generation_execution.1"
SOURCE_SCHEMA="v75.2t.offline_paper_order_generation_authorization.1"

class OrderGenerationExecutionError(ValueError): pass

def canonical_json(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(x:Any)->str:
    return hashlib.sha256(canonical_json(x).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: x=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OrderGenerationExecutionError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OrderGenerationExecutionError(f"invalid JSON: {path}") from e
    if not isinstance(x,dict): raise OrderGenerationExecutionError("top-level JSON must be an object")
    return x

def parse_ts(v:Any,name:str)->datetime:
    if not isinstance(v,str) or not v: raise OrderGenerationExecutionError(f"{name} invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OrderGenerationExecutionError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None: raise OrderGenerationExecutionError(f"{name} must include timezone")
    return d

def validate_config(c:Dict[str,Any])->None:
    if c.get("execution_scope")!="OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY":
        raise OrderGenerationExecutionError("execution_scope invalid")
    if c.get("order_type")!="MARKET_REFERENCE_ONLY":
        raise OrderGenerationExecutionError("order_type invalid")
    if c.get("time_in_force")!="DAY":
        raise OrderGenerationExecutionError("time_in_force invalid")
    for k in ("require_authorization_integrity","require_single_use_token",
              "require_token_unconsumed","require_token_unexpired",
              "require_manifest_integrity","prevent_output_overwrite"):
        if c.get(k) is not True: raise OrderGenerationExecutionError(f"{k} must be true")
    for k in ("order_submission_allowed","fill_simulation_allowed","paper_broker_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed",
              "external_side_effects_allowed"):
        if c.get(k) is not False: raise OrderGenerationExecutionError(f"{k} must be false")

def validate_source(s:Dict[str,Any],when:datetime)->None:
    if s.get("status")!="PASS": raise OrderGenerationExecutionError("authorization status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise OrderGenerationExecutionError("unsupported authorization schema")
    if s.get("authorization_state")!="AUTHORIZED_NOT_EXECUTED":
        raise OrderGenerationExecutionError("authorization not executable")
    if s.get("authorization_scope")!="OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY":
        raise OrderGenerationExecutionError("authorization scope invalid")
    if s.get("order_generation_authorized") is not True or s.get("order_generation_executed") is not False:
        raise OrderGenerationExecutionError("order generation authorization state invalid")
    if s.get("token_consumed") is not False: raise OrderGenerationExecutionError("token already consumed")

    observed=s.get("offline_paper_order_generation_authorization_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_order_generation_authorization_sha256",None)
    if observed!=sha256_of(clone): raise OrderGenerationExecutionError("authorization integrity failed")
    for f,h in (("authorization_checks","authorization_checks_sha256"),
                ("authorization_ledger","authorization_ledger_sha256"),
                ("authorization_token","authorization_token_sha256"),
                ("authorized_order_intent_manifest","authorized_order_intent_manifest_sha256")):
        if s.get(h)!=sha256_of(s.get(f)): raise OrderGenerationExecutionError(f"{f} integrity failed")

    token=s.get("authorization_token")
    if not isinstance(token,dict): raise OrderGenerationExecutionError("authorization token required")
    material={k:token.get(k) for k in ("authorization_id","validation_id","issued_at","expires_at","nonce","scope","authorized_order_intent_ids")}
    if token.get("token_sha256")!=sha256_of(material): raise OrderGenerationExecutionError("token integrity failed")
    if token.get("single_use") is not True or token.get("consumed") is not False:
        raise OrderGenerationExecutionError("token single-use state invalid")
    if token.get("token_state")!="ISSUED_NOT_CONSUMED" or token.get("consumed_at") is not None:
        raise OrderGenerationExecutionError("token state invalid")
    issued=parse_ts(token.get("issued_at"),"issued_at"); expires=parse_ts(token.get("expires_at"),"expires_at")
    if when<issued: raise OrderGenerationExecutionError("execution before token issuance")
    if when>expires: raise OrderGenerationExecutionError("authorization token expired")
    if token.get("authorization_id")!=s.get("authorization_id") or token.get("validation_id")!=s.get("validation_id"):
        raise OrderGenerationExecutionError("token identity mismatch")
    if token.get("scope")!=s.get("authorization_scope"): raise OrderGenerationExecutionError("token scope mismatch")

    manifest=s.get("authorized_order_intent_manifest")
    if not isinstance(manifest,list) or not manifest:
        raise OrderGenerationExecutionError("authorized order intent manifest required")
    ids=[x.get("order_intent_id") for x in manifest]
    if token.get("authorized_order_intent_ids")!=ids:
        raise OrderGenerationExecutionError("token order intent lock mismatch")
    for x in manifest:
        if x.get("order_object_creation_authorized") is not True:
            raise OrderGenerationExecutionError("order intent not authorized")
        if x.get("side") not in ("BUY","SELL"):
            raise OrderGenerationExecutionError("invalid order side")
        if x.get("quantity")!=1:
            raise OrderGenerationExecutionError("authorized quantity must be 1")
        if x.get("order_created") is not False or x.get("order_submitted") is not False:
            raise OrderGenerationExecutionError("order side effect detected")

    gate=s.get("authorization_gate",{})
    expected={"order_generation_authorized":True,"order_object_creation_execution_allowed":True,
              "order_object_creation_allowed":False,"order_submission_allowed":False,
              "fill_simulation_allowed":False,"paper_orders_allowed":False,
              "live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OrderGenerationExecutionError(f"authorization_gate {k} invalid")
    for k in ("order_submission_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise OrderGenerationExecutionError(f"{k} must be false")
    if s.get("order_objects_created")!=0 or s.get("orders_created")!=0 or s.get("orders_submitted")!=0:
        raise OrderGenerationExecutionError("order side effects detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise OrderGenerationExecutionError("safety violation")

def paper_order_id(auth_id:str,intent_id:str,created_at:str)->str:
    return "PORD-"+hashlib.sha256(f"{auth_id}|{intent_id}|{created_at}|{VERSION}".encode()).hexdigest()[:16].upper()

def build_execution(source:Dict[str,Any],config:Dict[str,Any],executed_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    when=datetime.now(timezone.utc).replace(microsecond=0) if executed_at is None else parse_ts(executed_at,"executed_at")
    validate_source(source,when)
    ts=when.isoformat()

    orders=[]
    for item in source["authorized_order_intent_manifest"]:
        order={"paper_order_id":paper_order_id(source["authorization_id"],item["order_intent_id"],ts),
               "authorization_id":source["authorization_id"],
               "order_intent_id":item["order_intent_id"],
               "symbol":item["symbol"],"side":item["side"],"quantity":item["quantity"],
               "order_type":config["order_type"],"time_in_force":config["time_in_force"],
               "reference_price":item["reference_price"],"created_at":ts,
               "order_state":"CREATED_NOT_SUBMITTED","offline_paper_object":True,
               "submitted":False,"filled":False,"fill_simulated":False,
               "broker_routed":False,"network_used":False,"external_side_effects":False}
        orders.append(order)

    token=copy.deepcopy(source["authorization_token"])
    token.update({"consumed":True,"consumed_at":ts,"token_state":"CONSUMED"})

    eid="OGE-"+hashlib.sha256(f"{source['authorization_id']}|{ts}|{VERSION}".encode()).hexdigest()[:16].upper()
    package={"execution_id":eid,"authorization_id":source["authorization_id"],
             "validation_id":source["validation_id"],"source_execution_id":source["execution_id"],
             "session_id":source["session_id"],"cycle_id":source["cycle_id"],
             "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
             "created_at":ts,"immutable":True,"offline_only":True,
             "paper_order_count":len(orders),"paper_orders":orders,
             "orders_submitted":0,"fills_created":0,"network_source":False}
    checks=[
      {"check_index":1,"check":"ORDER_GENERATION_AUTHORIZATION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"AUTHORIZATION_TOKEN_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"AUTHORIZATION_TOKEN_TIME_WINDOW","state":"PASS"},
      {"check_index":4,"check":"AUTHORIZATION_TOKEN_SINGLE_USE","state":"CONSUMED"},
      {"check_index":5,"check":"ORDER_INTENT_IDENTITY_LOCK","state":"LOCKED"},
      {"check_index":6,"check":"OFFLINE_PAPER_ORDER_OBJECTS_CREATED","state":"PASS"},
      {"check_index":7,"check":"ORDER_SUBMISSION_NOT_STARTED","state":"PASS"},
      {"check_index":8,"check":"FILL_SIMULATION_NOT_STARTED","state":"PASS"},
      {"check_index":9,"check":"BROKER_ROUTING_NOT_STARTED","state":"PASS"},
      {"check_index":10,"check":"ZERO_EXTERNAL_SIDE_EFFECTS","state":"PASS"},
      {"check_index":11,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    ledger=[
      {"ledger_index":1,"event":"ORDER_GENERATION_AUTHORIZATION_VERIFIED","state":"PASS","execution_id":eid},
      {"ledger_index":2,"event":"SINGLE_USE_TOKEN_CONSUMED","state":"CONSUMED","execution_id":eid},
      {"ledger_index":3,"event":"ORDER_INTENT_IDENTITIES_LOCKED","state":"LOCKED","execution_id":eid},
      {"ledger_index":4,"event":"OFFLINE_PAPER_ORDER_OBJECTS_CREATED","state":"PASS","execution_id":eid},
      {"ledger_index":5,"event":"ORDER_SUBMISSION_AND_FILL_BLOCKED","state":"ENFORCED","execution_id":eid},
      {"ledger_index":6,"event":"ORDER_GENERATION_EXECUTION_COMPLETED","state":"READY_FOR_ORDER_OBJECT_VALIDATION","execution_id":eid}]
    out={"status":"PASS","decision":"offline_paper_order_generation_executed",
         "execution_id":eid,"execution_state":"READY_FOR_ORDER_OBJECT_VALIDATION",
         "authorization_id":source["authorization_id"],"authorization_state":"CONSUMED",
         "order_generation_authorized":True,"order_generation_executed":True,
         "order_objects_created":len(orders),"token_consumed":True,
         "consumed_authorization_token":token,
         "consumed_authorization_token_sha256":sha256_of(token),
         "paper_order_package":package,"paper_order_package_sha256":sha256_of(package),
         "execution_checks":checks,"execution_checks_sha256":sha256_of(checks),
         "execution_ledger":ledger,"execution_ledger_sha256":sha256_of(ledger),
         "source_order_generation_authorization_sha256":source["offline_paper_order_generation_authorization_sha256"],
         "source_order_intent_validation_sha256":source["source_order_intent_validation_sha256"],
         "source_order_intent_execution_sha256":source["source_order_intent_execution_sha256"],
         "source_order_intent_package_sha256":source["source_order_intent_package_sha256"],
         "validation_id":source["validation_id"],"source_execution_id":source["execution_id"],
         "session_id":source["session_id"],"cycle_id":source["cycle_id"],
         "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
         "execution_gate":{"order_objects_created":True,"order_object_validation_allowed":True,
                           "order_submission_allowed":False,"fill_simulation_allowed":False,
                           "paper_broker_allowed":False,"live_orders_allowed":False,
                           "network_allowed":False,"next_version":"75.2V"},
         "order_submission_allowed":False,"fill_simulation_allowed":False,
         "paper_broker_allowed":False,"live_orders_allowed":False,
         "network_allowed":False,"broker_connection_allowed":False,
         "orders_submitted":0,"fills_created":0,"approved_for_live":False,"network_used":False,
         "safety_lock":copy.deepcopy(source["safety_lock"]),"executed_at":ts,
         "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_order_generation_execution_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path,prevent:bool=True)->None:
    d.mkdir(parents=True,exist_ok=True)
    primary=d/"offline_paper_order_generation_execution_v75_2u.json"
    if prevent and primary.exists():
        raise OrderGenerationExecutionError(f"execution output already exists: {primary}")
    payloads={
      "offline_paper_order_generation_execution_v75_2u.json":out,
      "offline_paper_order_objects_v75_2u.json":out["paper_order_package"],
      "offline_paper_order_generation_consumed_token_v75_2u.json":out["consumed_authorization_token"],
      "offline_paper_order_generation_execution_checks_v75_2u.json":{"execution_id":out["execution_id"],"execution_checks":out["execution_checks"],"execution_checks_sha256":out["execution_checks_sha256"]},
      "offline_paper_order_generation_execution_ledger_v75_2u.json":{"execution_id":out["execution_id"],"execution_ledger":out["execution_ledger"],"execution_ledger_sha256":out["execution_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_order_generation_execution_v75_2u.sha256").write_text(out["offline_paper_order_generation_execution_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--authorization",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--executed-at")
    a=p.parse_args(argv)
    try:
        c=read_json(Path(a.config))
        out=build_execution(read_json(Path(a.authorization)),c,a.executed_at)
        write_outputs(out,Path(a.output_dir),c.get("prevent_output_overwrite",True))
        first=out["paper_order_package"]["paper_orders"][0]
        print(json.dumps({"status":out["status"],"decision":out["decision"],
          "execution_id":out["execution_id"],"execution_state":out["execution_state"],
          "authorization_state":out["authorization_state"],
          "order_objects_created":out["order_objects_created"],
          "first_paper_order":{"paper_order_id":first["paper_order_id"],
                               "order_intent_id":first["order_intent_id"],
                               "symbol":first["symbol"],"side":first["side"],
                               "quantity":first["quantity"],"order_type":first["order_type"],
                               "time_in_force":first["time_in_force"],
                               "reference_price":first["reference_price"],
                               "order_state":first["order_state"]},
          "token_consumed":True,"order_object_validation_allowed":True,
          "order_submission_allowed":False,"orders_submitted":0,
          "fill_simulation_allowed":False,"fills_created":0,
          "paper_broker_allowed":False,"network_allowed":False,
          "approved_for_live":False,"network_used":False,
          "offline_paper_order_generation_execution_sha256":out["offline_paper_order_generation_execution_sha256"]},indent=2,sort_keys=True))
        return 0
    except (OrderGenerationExecutionError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_order_generation_execution_failed",
          "error":str(e),"approved_for_live":False,"network_used":False,
          "order_objects_created":0,"orders_submitted":0,"fills_created":0,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
