from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2S"
SCHEMA="v75.2s.offline_paper_order_intent_validation.1"
SOURCE_SCHEMA="v75.2r.offline_paper_order_intent_execution.1"

class OrderIntentValidationError(ValueError): pass

def canonical_json(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(x:Any)->str:
    return hashlib.sha256(canonical_json(x).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: x=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OrderIntentValidationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OrderIntentValidationError(f"invalid JSON: {path}") from e
    if not isinstance(x,dict): raise OrderIntentValidationError("top-level JSON must be an object")
    return x

def validate_config(c:Dict[str,Any])->None:
    if c.get("validation_scope")!="OFFLINE_PAPER_ORDER_INTENT_ONLY":
        raise OrderIntentValidationError("validation_scope invalid")
    if c.get("expected_intent_type")!="MARKET_REFERENCE_ONLY":
        raise OrderIntentValidationError("expected_intent_type invalid")
    for k in ("require_execution_integrity","require_package_integrity","require_consumed_token",
              "require_intent_id_recalculation","require_signal_intent_consistency",
              "require_positive_reference_price","require_zero_orders","require_safety_lock"):
        if c.get(k) is not True: raise OrderIntentValidationError(f"{k} must be true")
    for k in ("order_generation_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if c.get(k) is not False: raise OrderIntentValidationError(f"{k} must be false")

def expected_intent_id(auth_id:str,signal_id:str,created_at:str)->str:
    return "INT-"+hashlib.sha256(f"{auth_id}|{signal_id}|{created_at}|75.2R".encode()).hexdigest()[:16].upper()

def validate_source(s:Dict[str,Any])->Dict[str,Any]:
    if s.get("status")!="PASS": raise OrderIntentValidationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise OrderIntentValidationError("unsupported source schema")
    if s.get("execution_state")!="READY_FOR_ORDER_INTENT_VALIDATION":
        raise OrderIntentValidationError("source not ready for order intent validation")
    if s.get("authorization_state")!="CONSUMED" or s.get("token_consumed") is not True:
        raise OrderIntentValidationError("authorization token must be consumed")

    observed=s.get("offline_paper_order_intent_execution_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_order_intent_execution_sha256",None)
    if observed!=sha256_of(clone): raise OrderIntentValidationError("execution integrity failed")
    for field,hash_field in (
        ("execution_checks","execution_checks_sha256"),
        ("execution_ledger","execution_ledger_sha256"),
        ("consumed_authorization_token","consumed_authorization_token_sha256"),
        ("order_intent_package","order_intent_package_sha256")):
        if s.get(hash_field)!=sha256_of(s.get(field)):
            raise OrderIntentValidationError(f"{field} integrity failed")

    token=s.get("consumed_authorization_token")
    if not isinstance(token,dict) or token.get("consumed") is not True or token.get("token_state")!="CONSUMED":
        raise OrderIntentValidationError("consumed token invalid")
    if token.get("single_use") is not True or not token.get("consumed_at"):
        raise OrderIntentValidationError("single-use token evidence invalid")

    gate=s.get("execution_gate",{})
    expected={"order_intent_created":True,"order_intent_validation_allowed":True,
              "order_generation_allowed":False,"fill_simulation_allowed":False,
              "paper_orders_allowed":False,"live_orders_allowed":False,
              "network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OrderIntentValidationError(f"execution_gate {k} invalid")

    package=s.get("order_intent_package")
    if not isinstance(package,dict): raise OrderIntentValidationError("order_intent_package required")
    if package.get("immutable") is not True or package.get("network_source") is not False:
        raise OrderIntentValidationError("order intent package must be immutable offline data")
    if package.get("execution_id")!=s.get("execution_id") or package.get("authorization_id")!=s.get("authorization_id"):
        raise OrderIntentValidationError("package identity mismatch")
    intents=package.get("order_intents")
    if not isinstance(intents,list) or not intents: raise OrderIntentValidationError("order intents required")
    if package.get("order_intent_count")!=len(intents) or s.get("order_intents_created")!=len(intents):
        raise OrderIntentValidationError("order intent count mismatch")

    seen=set()
    for intent in intents:
        iid=intent.get("order_intent_id")
        if not isinstance(iid,str) or not iid.startswith("INT-"): raise OrderIntentValidationError("invalid order_intent_id")
        if iid in seen: raise OrderIntentValidationError("duplicate order_intent_id")
        seen.add(iid)
        expected_id=expected_intent_id(intent["authorization_id"],intent["signal_id"],intent["created_at"])
        if iid!=expected_id: raise OrderIntentValidationError("order_intent_id mismatch")
        if intent.get("intent_type")!="MARKET_REFERENCE_ONLY":
            raise OrderIntentValidationError("intent_type invalid")
        action=intent.get("signal_action"); intent_action=intent.get("intent_action")
        expected_action="NO_ACTION" if action=="HOLD" else action
        if intent_action!=expected_action: raise OrderIntentValidationError("signal/intent action mismatch")
        quantity=intent.get("quantity")
        if action=="HOLD":
            if quantity!=0: raise OrderIntentValidationError("HOLD quantity must be 0")
        elif quantity!=1:
            raise OrderIntentValidationError("actionable intent quantity must be 1")
        price=intent.get("reference_price")
        if not isinstance(price,(int,float)) or isinstance(price,bool) or price<=0:
            raise OrderIntentValidationError("reference_price must be positive")
        for key in ("order_created","order_submitted","fill_simulated","broker_routed","network_used"):
            if intent.get(key) is not False: raise OrderIntentValidationError(f"intent {key} must be false")

    for k in ("order_generation_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise OrderIntentValidationError(f"{k} must be false")
    if s.get("orders_created")!=0 or s.get("orders_submitted")!=0:
        raise OrderIntentValidationError("order side effects detected")
    if package.get("orders_created")!=0 or package.get("orders_submitted")!=0:
        raise OrderIntentValidationError("package order side effects detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise OrderIntentValidationError("live/network safety violation")
    lock=s.get("safety_lock")
    if not isinstance(lock,dict) or lock.get("lock_state")!="ENFORCED":
        raise OrderIntentValidationError("safety lock invalid")
    return package

def validation_id(execution_id:str,validated_at:str)->str:
    return "OIV-"+hashlib.sha256(f"{execution_id}|{validated_at}|{VERSION}".encode()).hexdigest()[:16].upper()

def build_validation(source:Dict[str,Any],config:Dict[str,Any],validated_at:str)->Dict[str,Any]:
    validate_config(config); package=validate_source(source)
    vid=validation_id(source["execution_id"],validated_at)
    intents=copy.deepcopy(package["order_intents"])
    checks=[
      {"check_index":1,"check":"ORDER_INTENT_EXECUTION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"ORDER_INTENT_PACKAGE_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"CONSUMED_TOKEN_EVIDENCE","state":"PASS"},
      {"check_index":4,"check":"ORDER_INTENT_COUNT_CONSISTENCY","state":"PASS"},
      {"check_index":5,"check":"ORDER_INTENT_ID_RECALCULATION","state":"PASS"},
      {"check_index":6,"check":"SIGNAL_INTENT_ACTION_CONSISTENCY","state":"PASS"},
      {"check_index":7,"check":"INTENT_QUANTITY_POLICY","state":"PASS"},
      {"check_index":8,"check":"REFERENCE_PRICE_VALIDITY","state":"PASS"},
      {"check_index":9,"check":"ORDER_GENERATION_NOT_STARTED","state":"PASS"},
      {"check_index":10,"check":"ZERO_ORDER_SIDE_EFFECTS","state":"PASS"},
      {"check_index":11,"check":"NETWORK_AND_BROKER_DISABLED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    ledger=[
      {"ledger_index":1,"event":"ORDER_INTENT_EXECUTION_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":2,"event":"ORDER_INTENT_PACKAGE_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":3,"event":"ORDER_INTENT_IDENTITIES_RECALCULATED","state":"PASS","validation_id":vid},
      {"ledger_index":4,"event":"ORDER_INTENT_POLICY_VERIFIED","state":"PASS","validation_id":vid},
      {"ledger_index":5,"event":"SAFETY_LOCKS_RECONFIRMED","state":"ENFORCED","validation_id":vid},
      {"ledger_index":6,"event":"ORDER_INTENT_VALIDATION_COMPLETED","state":"READY_FOR_ORDER_GENERATION_AUTHORIZATION","validation_id":vid}]
    summary={"order_intent_count":len(intents),
             "buy_intent_count":sum(1 for x in intents if x["intent_action"]=="BUY"),
             "sell_intent_count":sum(1 for x in intents if x["intent_action"]=="SELL"),
             "no_action_intent_count":sum(1 for x in intents if x["intent_action"]=="NO_ACTION"),
             "symbols":[x["symbol"] for x in intents],
             "total_intended_quantity":sum(x["quantity"] for x in intents)}
    out={"status":"PASS","decision":"offline_paper_order_intent_validated",
         "validation_id":vid,"validation_state":"READY_FOR_ORDER_GENERATION_AUTHORIZATION",
         "execution_id":source["execution_id"],"authorization_id":source["authorization_id"],
         "session_id":source["session_id"],"cycle_id":source["cycle_id"],
         "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
         "validated_order_intent_summary":summary,"validated_order_intents":intents,
         "validation_checks":checks,"validation_checks_sha256":sha256_of(checks),
         "validation_ledger":ledger,"validation_ledger_sha256":sha256_of(ledger),
         "source_order_intent_execution_sha256":source["offline_paper_order_intent_execution_sha256"],
         "source_order_intent_package_sha256":source["order_intent_package_sha256"],
         "validation_gate":{"order_intent_validated":True,"order_generation_authorization_allowed":True,
                           "order_generation_allowed":False,"fill_simulation_allowed":False,
                           "paper_orders_allowed":False,"live_orders_allowed":False,
                           "network_allowed":False,"next_version":"75.2T"},
         "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
         "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
         "orders_created":0,"orders_submitted":0,"approved_for_live":False,"network_used":False,
         "safety_lock":copy.deepcopy(source["safety_lock"]),"validated_at":validated_at,
         "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_order_intent_validation_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={"offline_paper_order_intent_validation_v75_2s.json":out,
              "offline_paper_validated_order_intents_v75_2s.json":{"validation_id":out["validation_id"],"validated_order_intent_summary":out["validated_order_intent_summary"],"validated_order_intents":out["validated_order_intents"]},
              "offline_paper_order_intent_validation_checks_v75_2s.json":{"validation_id":out["validation_id"],"validation_checks":out["validation_checks"],"validation_checks_sha256":out["validation_checks_sha256"]},
              "offline_paper_order_intent_validation_ledger_v75_2s.json":{"validation_id":out["validation_id"],"validation_ledger":out["validation_ledger"],"validation_ledger_sha256":out["validation_ledger_sha256"]}}
    for n,p in payloads.items(): (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_order_intent_validation_v75_2s.sha256").write_text(out["offline_paper_order_intent_validation_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--validated-at")
    a=p.parse_args(argv)
    try:
        import datetime
        ts=a.validated_at or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
        out=build_validation(read_json(Path(a.input)),read_json(Path(a.config)),ts)
        write_outputs(out,Path(a.output_dir))
        first=out["validated_order_intents"][0]
        print(json.dumps({"status":out["status"],"decision":out["decision"],
          "validation_id":out["validation_id"],"validation_state":out["validation_state"],
          **out["validated_order_intent_summary"],
          "first_order_intent":{"order_intent_id":first["order_intent_id"],"symbol":first["symbol"],
                                "signal_action":first["signal_action"],"intent_action":first["intent_action"],
                                "quantity":first["quantity"],"reference_price":first["reference_price"]},
          "order_generation_authorization_allowed":True,"order_generation_allowed":False,
          "orders_created":0,"orders_submitted":0,"network_allowed":False,
          "approved_for_live":False,"network_used":False,
          "offline_paper_order_intent_validation_sha256":out["offline_paper_order_intent_validation_sha256"]},indent=2,sort_keys=True))
        return 0
    except (OrderIntentValidationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_order_intent_validation_failed",
          "error":str(e),"approved_for_live":False,"network_used":False,
          "orders_created":0,"orders_submitted":0,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
