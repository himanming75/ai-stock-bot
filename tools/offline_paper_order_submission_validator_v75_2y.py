from __future__ import annotations
import argparse, copy, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2Y"
SCHEMA="v75.2y.offline_paper_order_submission_validation.1"
SOURCE_SCHEMA="v75.2x.offline_paper_order_submission_execution.1"

class OrderSubmissionValidationError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OrderSubmissionValidationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OrderSubmissionValidationError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OrderSubmissionValidationError("top-level JSON must be an object")
    return v

def parse_ts(v:Any,name:str)->datetime:
    if not isinstance(v,str) or not v: raise OrderSubmissionValidationError(f"{name} invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OrderSubmissionValidationError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None: raise OrderSubmissionValidationError(f"{name} must include timezone")
    return d

def expected_submission_id(execution_id:str,paper_order_id:str,submitted_at:str)->str:
    return "OSUB-"+hashlib.sha256(f"{execution_id}|{paper_order_id}|{submitted_at}".encode()).hexdigest()[:16].upper()

def validate_config(c:Dict[str,Any])->None:
    if c.get("validation_scope")!="OFFLINE_PAPER_ORDER_SUBMISSION_VALIDATION_ONLY":
        raise OrderSubmissionValidationError("validation_scope invalid")
    if c.get("required_order_state")!="SUBMITTED_OFFLINE_REFERENCE":
        raise OrderSubmissionValidationError("required_order_state invalid")
    for k in ("require_execution_integrity","require_package_integrity",
              "require_consumed_token_integrity","require_submission_id_recalculation",
              "require_zero_external_orders","require_zero_broker_routes",
              "require_zero_fills","require_safety_lock"):
        if c.get(k) is not True: raise OrderSubmissionValidationError(f"{k} must be true")
    for k in ("external_order_submission_allowed","broker_routing_allowed",
              "fill_simulation_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False: raise OrderSubmissionValidationError(f"{k} must be false")

def validate_source(s:Dict[str,Any],c:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS": raise OrderSubmissionValidationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise OrderSubmissionValidationError("unsupported source schema")
    if s.get("execution_state")!="READY_FOR_SUBMISSION_VALIDATION":
        raise OrderSubmissionValidationError("source not ready for submission validation")
    if s.get("order_submission_authorized") is not True or s.get("order_submission_executed") is not True:
        raise OrderSubmissionValidationError("submission execution state invalid")
    if s.get("authorization_state")!="CONSUMED" or s.get("token_consumed") is not True:
        raise OrderSubmissionValidationError("authorization token not consumed")

    observed=s.get("offline_paper_order_submission_execution_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_order_submission_execution_sha256",None)
    if observed!=sha256_of(clone): raise OrderSubmissionValidationError("execution integrity failed")
    for field,h in (("offline_submission_package","offline_submission_package_sha256"),
                    ("consumed_authorization_token","consumed_authorization_token_sha256"),
                    ("execution_checks","execution_checks_sha256"),
                    ("execution_ledger","execution_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(field)): raise OrderSubmissionValidationError(f"{field} integrity failed")

    gate=s.get("execution_gate",{})
    expected={"offline_submission_recorded":True,"submission_validation_allowed":True,
              "external_order_submission_allowed":False,"broker_routing_allowed":False,
              "fill_simulation_allowed":False,"paper_broker_allowed":False,
              "live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OrderSubmissionValidationError(f"execution_gate {k} invalid")

    token=s.get("consumed_authorization_token")
    if not isinstance(token,dict): raise OrderSubmissionValidationError("consumed token required")
    if token.get("single_use") is not True or token.get("consumed") is not True:
        raise OrderSubmissionValidationError("consumed token state invalid")
    if token.get("token_state")!="CONSUMED" or not token.get("consumed_at"):
        raise OrderSubmissionValidationError("consumed token evidence invalid")
    issued=parse_ts(token.get("issued_at"),"issued_at")
    expires=parse_ts(token.get("expires_at"),"expires_at")
    consumed=parse_ts(token.get("consumed_at"),"consumed_at")
    if consumed<issued or consumed>expires:
        raise OrderSubmissionValidationError("token consumed outside validity window")
    if token.get("authorization_id")!=s.get("authorization_id"):
        raise OrderSubmissionValidationError("token authorization identity mismatch")
    if token.get("validation_id")!=s.get("validation_id"):
        raise OrderSubmissionValidationError("token validation identity mismatch")

    package=s.get("offline_submission_package")
    if not isinstance(package,dict): raise OrderSubmissionValidationError("submission package required")
    if package.get("immutable") is not True or package.get("offline_only") is not True:
        raise OrderSubmissionValidationError("submission package must be immutable and offline-only")
    if package.get("network_source") is not False:
        raise OrderSubmissionValidationError("submission package network source invalid")
    orders=package.get("submitted_orders")
    if not isinstance(orders,list) or not orders:
        raise OrderSubmissionValidationError("submitted orders required")
    if package.get("submitted_order_count")!=len(orders):
        raise OrderSubmissionValidationError("submitted order count mismatch")
    if s.get("offline_submissions_recorded")!=len(orders):
        raise OrderSubmissionValidationError("source submission count mismatch")
    if token.get("authorized_paper_order_ids")!=[o.get("paper_order_id") for o in orders]:
        raise OrderSubmissionValidationError("token paper-order identity lock mismatch")

    sid_set=set(); pid_set=set()
    for o in orders:
        sid=o.get("offline_submission_id"); pid=o.get("paper_order_id")
        if not isinstance(sid,str) or not re.fullmatch(r"OSUB-[0-9A-F]{16}",sid):
            raise OrderSubmissionValidationError("invalid offline_submission_id")
        if sid in sid_set: raise OrderSubmissionValidationError("duplicate offline_submission_id")
        sid_set.add(sid)
        if not isinstance(pid,str) or not re.fullmatch(r"PORD-[0-9A-F]{16}",pid):
            raise OrderSubmissionValidationError("invalid paper_order_id")
        if pid in pid_set: raise OrderSubmissionValidationError("duplicate paper_order_id")
        pid_set.add(pid)
        submitted_at=o.get("submitted_at"); parse_ts(submitted_at,"submitted_at")
        if sid!=expected_submission_id(s["submission_execution_id"],pid,submitted_at):
            raise OrderSubmissionValidationError("offline_submission_id recalculation failed")
        if o.get("authorization_id")!=s.get("authorization_id"):
            raise OrderSubmissionValidationError("order authorization identity mismatch")
        if o.get("previous_order_state")!="CREATED_NOT_SUBMITTED":
            raise OrderSubmissionValidationError("previous order state invalid")
        if o.get("order_state")!=c["required_order_state"]:
            raise OrderSubmissionValidationError("submitted order state invalid")
        if o.get("submitted_offline") is not True or o.get("external_submission") is not False:
            raise OrderSubmissionValidationError("offline submission flags invalid")
        for k in ("broker_routed","network_used","filled","fill_simulated","external_side_effects"):
            if o.get(k) is not False: raise OrderSubmissionValidationError(f"unsafe submitted order state: {k}")
        if o.get("symbol")!="SPY" or o.get("side") not in ("BUY","SELL"):
            raise OrderSubmissionValidationError("order identity or side invalid")
        if isinstance(o.get("quantity"),bool) or o.get("quantity")!=1:
            raise OrderSubmissionValidationError("quantity policy failed")
        if o.get("order_type")!="MARKET_REFERENCE_ONLY" or o.get("time_in_force")!="DAY":
            raise OrderSubmissionValidationError("order terms invalid")
        price=o.get("reference_price")
        if isinstance(price,bool) or not isinstance(price,(int,float)) or float(price)<=0:
            raise OrderSubmissionValidationError("reference price invalid")

    for k in ("external_order_submission_allowed","broker_routing_allowed",
              "fill_simulation_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise OrderSubmissionValidationError(f"{k} must be false")
    if s.get("external_orders_submitted")!=0 or s.get("broker_routes_created")!=0 or s.get("fills_created")!=0:
        raise OrderSubmissionValidationError("external side effect detected")
    if package.get("external_orders_submitted")!=0 or package.get("broker_routes_created")!=0 or package.get("fills_created")!=0:
        raise OrderSubmissionValidationError("package external side effect detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise OrderSubmissionValidationError("safety violation")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise OrderSubmissionValidationError("safety lock invalid")
    return orders

def build_validation(source:Dict[str,Any],config:Dict[str,Any],validated_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    orders=validate_source(source,config)
    when=datetime.now(timezone.utc).replace(microsecond=0) if validated_at is None else parse_ts(validated_at,"validated_at")
    ts=when.isoformat()
    vid="OSV-"+hashlib.sha256(
        f"{source['submission_execution_id']}|{source['offline_submission_package_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    validated=[{
        "offline_submission_id":o["offline_submission_id"],
        "paper_order_id":o["paper_order_id"],
        "order_intent_id":o["order_intent_id"],
        "authorization_id":o["authorization_id"],
        "symbol":o["symbol"],"side":o["side"],"quantity":o["quantity"],
        "order_type":o["order_type"],"time_in_force":o["time_in_force"],
        "reference_price":o["reference_price"],
        "previous_order_state":o["previous_order_state"],
        "order_state":o["order_state"],
        "submitted_offline":True,"external_submission":False,
        "broker_routed":False,"network_used":False,
        "filled":False,"fill_simulated":False,
        "validation_state":"PASS"
    } for o in orders]

    checks=[
      {"check_index":1,"check":"SUBMISSION_EXECUTION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"OFFLINE_SUBMISSION_PACKAGE_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"CONSUMED_SUBMISSION_TOKEN_INTEGRITY","state":"PASS"},
      {"check_index":4,"check":"SUBMISSION_COUNT_CONSISTENCY","state":"PASS"},
      {"check_index":5,"check":"SUBMISSION_ID_RECALCULATION","state":"PASS"},
      {"check_index":6,"check":"PAPER_ORDER_IDENTITY_LOCK","state":"LOCKED"},
      {"check_index":7,"check":"OFFLINE_SUBMISSION_STATE_POLICY","state":"PASS"},
      {"check_index":8,"check":"DUPLICATE_SUBMISSION_PROHIBITION","state":"PASS"},
      {"check_index":9,"check":"EXTERNAL_ORDER_SUBMISSION_BLOCKED","state":"PASS"},
      {"check_index":10,"check":"BROKER_ROUTING_AND_FILL_BLOCKED","state":"PASS"},
      {"check_index":11,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    ledger=[
      {"ledger_index":1,"event":"SUBMISSION_EXECUTION_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":2,"event":"OFFLINE_SUBMISSION_PACKAGE_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":3,"event":"SUBMISSION_IDENTITIES_RECALCULATED","state":"PASS","validation_id":vid},
      {"ledger_index":4,"event":"OFFLINE_SUBMISSION_STATE_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":5,"event":"EXTERNAL_SIDE_EFFECTS_RECONFIRMED_ZERO","state":"ENFORCED","validation_id":vid},
      {"ledger_index":6,"event":"SUBMISSION_VALIDATION_COMPLETED","state":"READY_FOR_FILL_SIMULATION_AUTHORIZATION","validation_id":vid}]
    out={"status":"PASS","decision":"offline_paper_order_submission_validated",
         "submission_validation_id":vid,
         "validation_state":"READY_FOR_FILL_SIMULATION_AUTHORIZATION",
         "submission_validated":True,"validated_submission_count":len(validated),
         "validated_submissions":validated,
         "validated_submissions_sha256":sha256_of(validated),
         "validation_checks":checks,"validation_checks_sha256":sha256_of(checks),
         "validation_ledger":ledger,"validation_ledger_sha256":sha256_of(ledger),
         "validation_gate":{"submission_validated":True,
            "fill_simulation_authorization_allowed":True,
            "external_order_submission_allowed":False,"broker_routing_allowed":False,
            "fill_simulation_allowed":False,"paper_broker_allowed":False,
            "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2Z"},
         "source_order_submission_execution_sha256":source["offline_paper_order_submission_execution_sha256"],
         "source_offline_submission_package_sha256":source["offline_submission_package_sha256"],
         "source_order_submission_authorization_sha256":source["source_order_submission_authorization_sha256"],
         "source_order_object_validation_sha256":source["source_order_object_validation_sha256"],
         "submission_execution_id":source["submission_execution_id"],
         "authorization_id":source["authorization_id"],"validation_id":source["validation_id"],
         "execution_id":source["execution_id"],"authorization_source_id":source["authorization_source_id"],
         "session_id":source["session_id"],"cycle_id":source["cycle_id"],
         "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
         "external_order_submission_allowed":False,"broker_routing_allowed":False,
         "fill_simulation_allowed":False,"paper_broker_allowed":False,
         "live_orders_allowed":False,"network_allowed":False,
         "broker_connection_allowed":False,"external_orders_submitted":0,
         "broker_routes_created":0,"fills_created":0,
         "approved_for_live":False,"network_used":False,
         "safety_lock":copy.deepcopy(source["safety_lock"]),
         "validated_at":ts,"schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_order_submission_validation_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_order_submission_validation_v75_2y.json":out,
      "offline_paper_validated_submissions_v75_2y.json":{"submission_validation_id":out["submission_validation_id"],"validated_submission_count":out["validated_submission_count"],"validated_submissions":out["validated_submissions"],"validated_submissions_sha256":out["validated_submissions_sha256"]},
      "offline_paper_order_submission_validation_checks_v75_2y.json":{"submission_validation_id":out["submission_validation_id"],"validation_checks":out["validation_checks"],"validation_checks_sha256":out["validation_checks_sha256"]},
      "offline_paper_order_submission_validation_ledger_v75_2y.json":{"submission_validation_id":out["submission_validation_id"],"validation_ledger":out["validation_ledger"],"validation_ledger_sha256":out["validation_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_order_submission_validation_v75_2y.sha256").write_text(
        out["offline_paper_order_submission_validation_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--validated-at")
    a=p.parse_args(argv)
    try:
        out=build_validation(read_json(Path(a.input)),read_json(Path(a.config)),a.validated_at)
        write_outputs(out,Path(a.output_dir))
        first=out["validated_submissions"][0]
        print(json.dumps({"status":out["status"],"decision":out["decision"],
          "submission_validation_id":out["submission_validation_id"],
          "validation_state":out["validation_state"],
          "validated_submission_count":out["validated_submission_count"],
          "first_validated_submission":first,
          "fill_simulation_authorization_allowed":True,
          "external_order_submission_allowed":False,"external_orders_submitted":0,
          "broker_routing_allowed":False,"broker_routes_created":0,
          "fill_simulation_allowed":False,"fills_created":0,
          "paper_broker_allowed":False,"network_allowed":False,
          "approved_for_live":False,"network_used":False,
          "offline_paper_order_submission_validation_sha256":out["offline_paper_order_submission_validation_sha256"]},indent=2,sort_keys=True))
        return 0
    except (OrderSubmissionValidationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_order_submission_validation_failed",
          "error":str(e),"approved_for_live":False,"network_used":False,
          "external_orders_submitted":0,"broker_routes_created":0,"fills_created":0,
          "version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
