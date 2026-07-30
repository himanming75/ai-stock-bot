from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2Z"
SCHEMA="v75.2z.offline_paper_fill_simulation_authorization.1"
SOURCE_SCHEMA="v75.2y.offline_paper_order_submission_validation.1"

class FillSimulationAuthorizationError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try:
        v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise FillSimulationAuthorizationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise FillSimulationAuthorizationError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict):
        raise FillSimulationAuthorizationError("top-level JSON must be an object")
    return v

def parse_ts(v:Any,name:str)->datetime:
    if not isinstance(v,str) or not v:
        raise FillSimulationAuthorizationError(f"{name} invalid")
    try:
        d=datetime.fromisoformat(v)
    except ValueError as e:
        raise FillSimulationAuthorizationError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None:
        raise FillSimulationAuthorizationError(f"{name} must include timezone")
    return d

def validate_config(c:Dict[str,Any])->None:
    if c.get("authorization_scope")!="OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY":
        raise FillSimulationAuthorizationError("authorization_scope invalid")
    ttl=c.get("authorization_ttl_seconds")
    if isinstance(ttl,bool) or not isinstance(ttl,int) or ttl<60 or ttl>3600:
        raise FillSimulationAuthorizationError("authorization_ttl_seconds must be 60..3600")
    if c.get("fill_price_policy")!="REFERENCE_PRICE_ONLY":
        raise FillSimulationAuthorizationError("fill_price_policy invalid")
    if c.get("fill_quantity_policy")!="FULL_QUANTITY_ONLY":
        raise FillSimulationAuthorizationError("fill_quantity_policy invalid")
    for k in ("require_validation_integrity","require_validated_submissions_integrity",
              "require_zero_existing_fills","require_single_use_token",
              "require_reference_price_lock","require_quantity_lock"):
        if c.get(k) is not True:
            raise FillSimulationAuthorizationError(f"{k} must be true")
    for k in ("fill_simulation_allowed","position_update_allowed","cash_update_allowed",
              "portfolio_update_allowed","external_order_submission_allowed",
              "broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False:
            raise FillSimulationAuthorizationError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS":
        raise FillSimulationAuthorizationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA:
        raise FillSimulationAuthorizationError("unsupported source schema")
    if s.get("validation_state")!="READY_FOR_FILL_SIMULATION_AUTHORIZATION":
        raise FillSimulationAuthorizationError("source not ready for fill simulation authorization")
    if s.get("submission_validated") is not True:
        raise FillSimulationAuthorizationError("submission validation not complete")

    observed=s.get("offline_paper_order_submission_validation_sha256")
    clone=copy.deepcopy(s)
    clone.pop("offline_paper_order_submission_validation_sha256",None)
    if observed!=sha256_of(clone):
        raise FillSimulationAuthorizationError("submission validation integrity failed")
    for field,h in (("validated_submissions","validated_submissions_sha256"),
                    ("validation_checks","validation_checks_sha256"),
                    ("validation_ledger","validation_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(field)):
            raise FillSimulationAuthorizationError(f"{field} integrity failed")

    gate=s.get("validation_gate",{})
    expected={
        "submission_validated":True,
        "fill_simulation_authorization_allowed":True,
        "fill_simulation_allowed":False,
        "external_order_submission_allowed":False,
        "broker_routing_allowed":False,
        "paper_broker_allowed":False,
        "live_orders_allowed":False,
        "network_allowed":False,
        "next_version":VERSION,
    }
    for k,v in expected.items():
        if gate.get(k)!=v:
            raise FillSimulationAuthorizationError(f"validation_gate {k} invalid")

    items=s.get("validated_submissions")
    if not isinstance(items,list) or not items:
        raise FillSimulationAuthorizationError("validated submissions required")
    if s.get("validated_submission_count")!=len(items):
        raise FillSimulationAuthorizationError("validated submission count mismatch")
    seen_submission=set()
    seen_order=set()
    for o in items:
        sid=o.get("offline_submission_id")
        pid=o.get("paper_order_id")
        if not isinstance(sid,str) or sid in seen_submission:
            raise FillSimulationAuthorizationError("duplicate or invalid offline submission id")
        if not isinstance(pid,str) or pid in seen_order:
            raise FillSimulationAuthorizationError("duplicate or invalid paper order id")
        seen_submission.add(sid)
        seen_order.add(pid)
        if o.get("validation_state")!="PASS":
            raise FillSimulationAuthorizationError("validated submission state invalid")
        if o.get("order_state")!="SUBMITTED_OFFLINE_REFERENCE":
            raise FillSimulationAuthorizationError("submission order state invalid")
        if o.get("submitted_offline") is not True:
            raise FillSimulationAuthorizationError("offline submission evidence missing")
        if o.get("external_submission") is not False:
            raise FillSimulationAuthorizationError("external submission detected")
        for k in ("broker_routed","network_used","filled","fill_simulated"):
            if o.get(k) is not False:
                raise FillSimulationAuthorizationError(f"unsafe validated submission state: {k}")
        if o.get("order_type")!="MARKET_REFERENCE_ONLY":
            raise FillSimulationAuthorizationError("unsupported order type")
        if o.get("time_in_force")!="DAY":
            raise FillSimulationAuthorizationError("unsupported time in force")
        q=o.get("quantity")
        if isinstance(q,bool) or not isinstance(q,int) or q<=0:
            raise FillSimulationAuthorizationError("quantity invalid")
        p=o.get("reference_price")
        if isinstance(p,bool) or not isinstance(p,(int,float)) or float(p)<=0:
            raise FillSimulationAuthorizationError("reference price invalid")

    for k in ("external_order_submission_allowed","broker_routing_allowed",
              "fill_simulation_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed"):
        if s.get(k) is not False:
            raise FillSimulationAuthorizationError(f"{k} must be false")
    if s.get("external_orders_submitted")!=0 or s.get("broker_routes_created")!=0 or s.get("fills_created")!=0:
        raise FillSimulationAuthorizationError("external side effect or existing fill detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise FillSimulationAuthorizationError("safety violation")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise FillSimulationAuthorizationError("safety lock invalid")
    return items

def build_authorization(source:Dict[str,Any],config:Dict[str,Any],issued_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    items=validate_source(source)
    when=datetime.now(timezone.utc).replace(microsecond=0) if issued_at is None else parse_ts(issued_at,"issued_at")
    expires=when+timedelta(seconds=config["authorization_ttl_seconds"])
    issued=when.isoformat()
    expiry=expires.isoformat()
    aid="FSA-"+hashlib.sha256(
        f"{source['submission_validation_id']}|{source['validated_submissions_sha256']}|{issued}|{VERSION}".encode()
    ).hexdigest()[:16].upper()
    nonce=hashlib.sha256(f"{aid}|{expiry}|fill-simulation".encode()).hexdigest()[:32]

    targets=[{
        "offline_submission_id":o["offline_submission_id"],
        "paper_order_id":o["paper_order_id"],
        "order_intent_id":o["order_intent_id"],
        "authorization_id":o["authorization_id"],
        "symbol":o["symbol"],"side":o["side"],"quantity":o["quantity"],
        "order_type":o["order_type"],"time_in_force":o["time_in_force"],
        "reference_price":o["reference_price"],
        "current_order_state":o["order_state"],
        "fill_price_policy":"REFERENCE_PRICE_ONLY",
        "fill_quantity_policy":"FULL_QUANTITY_ONLY",
        "fill_simulation_execution_authorized":True,
        "fill_object_created":False,
        "fill_simulated":False,
        "filled":False,
        "position_updated":False,
        "cash_updated":False,
        "portfolio_updated":False
    } for o in items]

    token_material={
        "fill_simulation_authorization_id":aid,
        "submission_validation_id":source["submission_validation_id"],
        "issued_at":issued,"expires_at":expiry,"nonce":nonce,
        "scope":"OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY",
        "authorized_offline_submission_ids":[o["offline_submission_id"] for o in targets],
        "authorized_paper_order_ids":[o["paper_order_id"] for o in targets],
        "fill_price_policy":"REFERENCE_PRICE_ONLY",
        "fill_quantity_policy":"FULL_QUANTITY_ONLY",
    }
    token={**token_material,
           "token_sha256":sha256_of(token_material),
           "single_use":True,"consumed":False,"consumed_at":None,
           "token_state":"ISSUED_NOT_CONSUMED"}

    checks=[
      {"check_index":1,"check":"SUBMISSION_VALIDATION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"VALIDATED_SUBMISSIONS_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"SUBMISSION_AND_ORDER_IDENTITIES_LOCKED","state":"LOCKED"},
      {"check_index":4,"check":"REFERENCE_PRICE_LOCK","state":"LOCKED"},
      {"check_index":5,"check":"FULL_QUANTITY_LOCK","state":"LOCKED"},
      {"check_index":6,"check":"NO_EXISTING_FILL_OBJECT","state":"PASS"},
      {"check_index":7,"check":"NO_EXISTING_POSITION_UPDATE","state":"PASS"},
      {"check_index":8,"check":"SINGLE_USE_TOKEN_POLICY","state":"ENFORCED"},
      {"check_index":9,"check":"FILL_SIMULATION_SCOPE_LIMIT","state":"ENFORCED"},
      {"check_index":10,"check":"BROKER_AND_EXTERNAL_SUBMISSION_BLOCKED","state":"PASS"},
      {"check_index":11,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    ledger=[
      {"ledger_index":1,"event":"SUBMISSION_VALIDATION_VERIFIED","state":"PASS","authorization_id":aid},
      {"ledger_index":2,"event":"FILL_SIMULATION_TARGETS_LOCKED","state":"LOCKED","authorization_id":aid},
      {"ledger_index":3,"event":"REFERENCE_PRICE_AND_QUANTITY_POLICIES_LOCKED","state":"LOCKED","authorization_id":aid},
      {"ledger_index":4,"event":"SINGLE_USE_FILL_SIMULATION_TOKEN_ISSUED","state":"ISSUED_NOT_CONSUMED","authorization_id":aid},
      {"ledger_index":5,"event":"POSITION_CASH_PORTFOLIO_UPDATES_BLOCKED","state":"ENFORCED","authorization_id":aid},
      {"ledger_index":6,"event":"FILL_SIMULATION_AUTHORIZATION_COMPLETED","state":"AUTHORIZED_NOT_EXECUTED","authorization_id":aid}]

    out={
      "status":"PASS",
      "decision":"offline_paper_fill_simulation_authorized",
      "fill_simulation_authorization_id":aid,
      "authorization_scope":"OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY",
      "authorization_state":"AUTHORIZED_NOT_EXECUTED",
      "fill_simulation_authorized":True,
      "fill_simulation_executed":False,
      "fill_simulation_execution_allowed":True,
      "fill_simulation_allowed":False,
      "authorized_target_count":len(targets),
      "authorized_fill_simulation_targets":targets,
      "authorized_fill_simulation_targets_sha256":sha256_of(targets),
      "fill_simulation_authorization_token":token,
      "fill_simulation_authorization_token_sha256":sha256_of(token),
      "authorization_checks":checks,
      "authorization_checks_sha256":sha256_of(checks),
      "authorization_ledger":ledger,
      "authorization_ledger_sha256":sha256_of(ledger),
      "authorization_gate":{
        "fill_simulation_authorized":True,
        "fill_simulation_execution_allowed":True,
        "fill_simulation_allowed":False,
        "fill_object_creation_allowed":False,
        "position_update_allowed":False,
        "cash_update_allowed":False,
        "portfolio_update_allowed":False,
        "external_order_submission_allowed":False,
        "broker_routing_allowed":False,
        "paper_broker_allowed":False,
        "live_orders_allowed":False,
        "network_allowed":False,
        "next_version":"75.2AA"
      },
      "source_order_submission_validation_sha256":source["offline_paper_order_submission_validation_sha256"],
      "source_validated_submissions_sha256":source["validated_submissions_sha256"],
      "source_order_submission_execution_sha256":source["source_order_submission_execution_sha256"],
      "source_order_submission_authorization_sha256":source["source_order_submission_authorization_sha256"],
      "submission_validation_id":source["submission_validation_id"],
      "submission_execution_id":source["submission_execution_id"],
      "authorization_id":source["authorization_id"],
      "validation_id":source["validation_id"],
      "execution_id":source["execution_id"],
      "authorization_source_id":source["authorization_source_id"],
      "session_id":source["session_id"],
      "cycle_id":source["cycle_id"],
      "cycle_sequence":source["cycle_sequence"],
      "champion_candidate_id":source["champion_candidate_id"],
      "issued_at":issued,"expires_at":expiry,
      "token_consumed":False,
      "fill_objects_created":0,
      "fills_created":0,
      "positions_updated":0,
      "cash_updates_created":0,
      "portfolio_updates_created":0,
      "external_orders_submitted":0,
      "broker_routes_created":0,
      "position_update_allowed":False,
      "cash_update_allowed":False,
      "portfolio_update_allowed":False,
      "external_order_submission_allowed":False,
      "broker_routing_allowed":False,
      "paper_broker_allowed":False,
      "live_orders_allowed":False,
      "network_allowed":False,
      "broker_connection_allowed":False,
      "approved_for_live":False,
      "network_used":False,
      "safety_lock":copy.deepcopy(source["safety_lock"]),
      "schema_version":SCHEMA,
      "version":VERSION
    }
    out["offline_paper_fill_simulation_authorization_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_fill_simulation_authorization_v75_2z.json":out,
      "offline_paper_fill_simulation_authorization_token_v75_2z.json":out["fill_simulation_authorization_token"],
      "offline_paper_authorized_fill_simulation_targets_v75_2z.json":{
        "fill_simulation_authorization_id":out["fill_simulation_authorization_id"],
        "authorized_target_count":out["authorized_target_count"],
        "authorized_fill_simulation_targets":out["authorized_fill_simulation_targets"],
        "authorized_fill_simulation_targets_sha256":out["authorized_fill_simulation_targets_sha256"]},
      "offline_paper_fill_simulation_authorization_checks_v75_2z.json":{
        "fill_simulation_authorization_id":out["fill_simulation_authorization_id"],
        "authorization_checks":out["authorization_checks"],
        "authorization_checks_sha256":out["authorization_checks_sha256"]},
      "offline_paper_fill_simulation_authorization_ledger_v75_2z.json":{
        "fill_simulation_authorization_id":out["fill_simulation_authorization_id"],
        "authorization_ledger":out["authorization_ledger"],
        "authorization_ledger_sha256":out["authorization_ledger_sha256"]}
    }
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_fill_simulation_authorization_v75_2z.sha256").write_text(
        out["offline_paper_fill_simulation_authorization_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--issued-at")
    a=p.parse_args(argv)
    try:
        out=build_authorization(read_json(Path(a.input)),read_json(Path(a.config)),a.issued_at)
        write_outputs(out,Path(a.output_dir))
        first=out["authorized_fill_simulation_targets"][0]
        print(json.dumps({
          "status":out["status"],
          "decision":out["decision"],
          "fill_simulation_authorization_id":out["fill_simulation_authorization_id"],
          "authorization_scope":out["authorization_scope"],
          "authorization_state":out["authorization_state"],
          "authorized_target_count":out["authorized_target_count"],
          "first_authorized_target":first,
          "expires_at":out["expires_at"],
          "token_state":out["fill_simulation_authorization_token"]["token_state"],
          "token_consumed":False,
          "fill_simulation_execution_allowed":True,
          "fill_simulation_allowed":False,
          "fill_objects_created":0,
          "fills_created":0,
          "positions_updated":0,
          "cash_updates_created":0,
          "portfolio_updates_created":0,
          "broker_routing_allowed":False,
          "network_allowed":False,
          "approved_for_live":False,
          "network_used":False,
          "offline_paper_fill_simulation_authorization_sha256":out["offline_paper_fill_simulation_authorization_sha256"]
        },indent=2,sort_keys=True))
        return 0
    except (FillSimulationAuthorizationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({
          "status":"FAIL",
          "decision":"offline_paper_fill_simulation_authorization_failed",
          "error":str(e),
          "approved_for_live":False,
          "network_used":False,
          "fill_objects_created":0,
          "fills_created":0,
          "positions_updated":0,
          "version":VERSION
        },indent=2,sort_keys=True))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
