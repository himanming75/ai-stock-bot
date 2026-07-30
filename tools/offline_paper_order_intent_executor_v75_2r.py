from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2R"
SCHEMA="v75.2r.offline_paper_order_intent_execution.1"
SOURCE_SCHEMA="v75.2q.offline_paper_order_intent_authorization.1"

class OrderIntentExecutionError(ValueError): pass

def canonical_json(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(x:Any)->str:
    return hashlib.sha256(canonical_json(x).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: x=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OrderIntentExecutionError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OrderIntentExecutionError(f"invalid JSON: {path}") from e
    if not isinstance(x,dict): raise OrderIntentExecutionError("top-level JSON must be an object")
    return x

def parse_ts(v:Any,name:str)->datetime:
    if not isinstance(v,str) or not v: raise OrderIntentExecutionError(f"{name} invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OrderIntentExecutionError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None: raise OrderIntentExecutionError(f"{name} must include timezone")
    return d

def validate_config(c:Dict[str,Any])->None:
    if c.get("execution_scope")!="OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY":
        raise OrderIntentExecutionError("execution_scope invalid")
    if c.get("default_quantity")!=1: raise OrderIntentExecutionError("default_quantity must be 1")
    if c.get("intent_type")!="MARKET_REFERENCE_ONLY": raise OrderIntentExecutionError("intent_type invalid")
    for k in ("require_authorization_integrity","require_single_use_token","require_token_unconsumed",
              "require_token_unexpired","require_signal_manifest_integrity","prevent_output_overwrite"):
        if c.get(k) is not True: raise OrderIntentExecutionError(f"{k} must be true")
    for k in ("order_generation_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False: raise OrderIntentExecutionError(f"{k} must be false")

def validate_source(s:Dict[str,Any],when:datetime)->None:
    if s.get("status")!="PASS": raise OrderIntentExecutionError("authorization status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise OrderIntentExecutionError("unsupported authorization schema")
    if s.get("authorization_state")!="AUTHORIZED_NOT_EXECUTED":
        raise OrderIntentExecutionError("authorization not executable")
    if s.get("authorization_scope")!="OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY":
        raise OrderIntentExecutionError("authorization scope invalid")
    if s.get("order_intent_authorized") is not True or s.get("order_intent_created") is not False:
        raise OrderIntentExecutionError("order intent authorization state invalid")
    if s.get("token_consumed") is not False: raise OrderIntentExecutionError("token already consumed")

    observed=s.get("offline_paper_order_intent_authorization_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_order_intent_authorization_sha256",None)
    if observed!=sha256_of(clone): raise OrderIntentExecutionError("authorization integrity failed")
    for f,h in (("authorization_checks","authorization_checks_sha256"),
                ("authorization_ledger","authorization_ledger_sha256"),
                ("authorization_token","authorization_token_sha256"),
                ("authorized_signal_manifest","authorized_signal_manifest_sha256")):
        if s.get(h)!=sha256_of(s.get(f)): raise OrderIntentExecutionError(f"{f} integrity failed")

    token=s.get("authorization_token")
    if not isinstance(token,dict): raise OrderIntentExecutionError("authorization token required")
    material={k:token.get(k) for k in ("authorization_id","validation_id","issued_at","expires_at","nonce","scope","authorized_signal_ids")}
    if token.get("token_sha256")!=sha256_of(material): raise OrderIntentExecutionError("token integrity failed")
    if token.get("single_use") is not True or token.get("consumed") is not False:
        raise OrderIntentExecutionError("token single-use state invalid")
    if token.get("token_state")!="ISSUED_NOT_CONSUMED" or token.get("consumed_at") is not None:
        raise OrderIntentExecutionError("token state invalid")
    issued=parse_ts(token.get("issued_at"),"issued_at"); expires=parse_ts(token.get("expires_at"),"expires_at")
    if when<issued: raise OrderIntentExecutionError("execution before token issuance")
    if when>expires: raise OrderIntentExecutionError("authorization token expired")
    if token.get("authorization_id")!=s.get("authorization_id") or token.get("validation_id")!=s.get("validation_id"):
        raise OrderIntentExecutionError("token identity mismatch")
    if token.get("scope")!=s.get("authorization_scope"): raise OrderIntentExecutionError("token scope mismatch")

    manifest=s.get("authorized_signal_manifest")
    if not isinstance(manifest,list) or not manifest: raise OrderIntentExecutionError("authorized signal manifest required")
    ids=[x.get("signal_id") for x in manifest]
    if token.get("authorized_signal_ids")!=ids: raise OrderIntentExecutionError("token signal lock mismatch")
    for x in manifest:
        if x.get("order_intent_creation_authorized") is not True: raise OrderIntentExecutionError("signal not authorized")
        if x.get("order_created") is not False or x.get("order_submitted") is not False:
            raise OrderIntentExecutionError("order side effect detected")
        if x.get("action") not in ("BUY","SELL","HOLD"): raise OrderIntentExecutionError("invalid signal action")

    gate=s.get("authorization_gate",{})
    expected={"order_intent_authorized":True,"order_intent_creation_execution_allowed":True,
              "order_intent_creation_allowed":False,"order_generation_allowed":False,
              "fill_simulation_allowed":False,"paper_orders_allowed":False,
              "live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OrderIntentExecutionError(f"authorization_gate {k} invalid")
    for k in ("order_generation_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise OrderIntentExecutionError(f"{k} must be false")
    if s.get("order_intents_created")!=0 or s.get("orders_created")!=0 or s.get("orders_submitted")!=0:
        raise OrderIntentExecutionError("side effects detected")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise OrderIntentExecutionError("safety violation")

def intent_id(auth_id:str,signal_id:str,executed_at:str)->str:
    return "INT-"+hashlib.sha256(f"{auth_id}|{signal_id}|{executed_at}|{VERSION}".encode()).hexdigest()[:16].upper()

def build_execution(source:Dict[str,Any],config:Dict[str,Any],executed_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    when=datetime.now(timezone.utc).replace(microsecond=0) if executed_at is None else parse_ts(executed_at,"executed_at")
    validate_source(source,when)
    ts=when.isoformat()
    intents=[]
    for sig in source["authorized_signal_manifest"]:
        action=sig["action"]
        intent_action="NO_ACTION" if action=="HOLD" else action
        material={"authorization_id":source["authorization_id"],"signal_id":sig["signal_id"],
                  "symbol":sig["symbol"],"signal_action":action,"intent_action":intent_action,
                  "intent_type":config["intent_type"],"quantity":config["default_quantity"] if action!="HOLD" else 0,
                  "reference_price":sig["latest_price"],"created_at":ts}
        intents.append({**material,"order_intent_id":intent_id(source["authorization_id"],sig["signal_id"],ts),
                        "order_created":False,"order_submitted":False,"fill_simulated":False,
                        "broker_routed":False,"network_used":False})
    token=copy.deepcopy(source["authorization_token"])
    token.update({"consumed":True,"consumed_at":ts,"token_state":"CONSUMED"})
    checks=[
      {"check_index":1,"check":"ORDER_INTENT_AUTHORIZATION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"AUTHORIZATION_TOKEN_INTEGRITY","state":"PASS"},
      {"check_index":3,"check":"AUTHORIZATION_TOKEN_TIME_WINDOW","state":"PASS"},
      {"check_index":4,"check":"AUTHORIZATION_TOKEN_SINGLE_USE","state":"CONSUMED"},
      {"check_index":5,"check":"AUTHORIZED_SIGNAL_MANIFEST_INTEGRITY","state":"PASS"},
      {"check_index":6,"check":"ORDER_INTENT_OBJECTS_CREATED","state":"PASS"},
      {"check_index":7,"check":"ORDER_GENERATION_NOT_STARTED","state":"PASS"},
      {"check_index":8,"check":"FILL_SIMULATION_NOT_STARTED","state":"PASS"},
      {"check_index":9,"check":"ZERO_ORDER_SIDE_EFFECTS","state":"PASS"},
      {"check_index":10,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":11,"check":"BROKER_DISCONNECTED","state":"PASS"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    eid="OIE-"+hashlib.sha256(f"{source['authorization_id']}|{ts}|{VERSION}".encode()).hexdigest()[:16].upper()
    ledger=[
      {"ledger_index":1,"event":"ORDER_INTENT_AUTHORIZATION_VERIFIED","state":"PASS","execution_id":eid},
      {"ledger_index":2,"event":"SINGLE_USE_TOKEN_CONSUMED","state":"CONSUMED","execution_id":eid},
      {"ledger_index":3,"event":"AUTHORIZED_SIGNAL_MANIFEST_LOADED","state":"LOCKED","execution_id":eid},
      {"ledger_index":4,"event":"ORDER_INTENT_OBJECTS_CREATED","state":"PASS","execution_id":eid},
      {"ledger_index":5,"event":"ORDER_SIDE_EFFECTS_BLOCKED","state":"ENFORCED","execution_id":eid},
      {"ledger_index":6,"event":"ORDER_INTENT_EXECUTION_COMPLETED","state":"READY_FOR_ORDER_INTENT_VALIDATION","execution_id":eid}]
    package={"execution_id":eid,"authorization_id":source["authorization_id"],"validation_id":source["validation_id"],
             "signal_execution_id":source["signal_execution_id"],"session_id":source["session_id"],
             "cycle_id":source["cycle_id"],"cycle_sequence":source["cycle_sequence"],
             "champion_candidate_id":source["champion_candidate_id"],"created_at":ts,
             "order_intents":intents,"order_intent_count":len(intents),"immutable":True,
             "orders_created":0,"orders_submitted":0,"network_source":False}
    out={"status":"PASS","decision":"offline_paper_order_intent_execution_completed",
         "execution_id":eid,"execution_state":"READY_FOR_ORDER_INTENT_VALIDATION",
         "authorization_id":source["authorization_id"],"authorization_state":"CONSUMED",
         "order_intent_authorized":True,"order_intent_created":True,"order_intents_created":len(intents),
         "token_consumed":True,"consumed_authorization_token":token,
         "consumed_authorization_token_sha256":sha256_of(token),
         "order_intent_package":package,"order_intent_package_sha256":sha256_of(package),
         "execution_checks":checks,"execution_checks_sha256":sha256_of(checks),
         "execution_ledger":ledger,"execution_ledger_sha256":sha256_of(ledger),
         "source_order_intent_authorization_sha256":source["offline_paper_order_intent_authorization_sha256"],
         "validation_id":source["validation_id"],"signal_execution_id":source["signal_execution_id"],
         "session_id":source["session_id"],"cycle_id":source["cycle_id"],"cycle_sequence":source["cycle_sequence"],
         "champion_candidate_id":source["champion_candidate_id"],
         "execution_gate":{"order_intent_created":True,"order_intent_validation_allowed":True,
                           "order_generation_allowed":False,"fill_simulation_allowed":False,
                           "paper_orders_allowed":False,"live_orders_allowed":False,
                           "network_allowed":False,"next_version":"75.2S"},
         "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
         "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
         "orders_created":0,"orders_submitted":0,"approved_for_live":False,"network_used":False,
         "safety_lock":copy.deepcopy(source["safety_lock"]),"executed_at":ts,
         "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_order_intent_execution_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path,prevent:bool=True)->None:
    d.mkdir(parents=True,exist_ok=True)
    primary=d/"offline_paper_order_intent_execution_v75_2r.json"
    if prevent and primary.exists(): raise OrderIntentExecutionError(f"execution output already exists: {primary}")
    payloads={"offline_paper_order_intent_execution_v75_2r.json":out,
              "offline_paper_order_intent_package_v75_2r.json":out["order_intent_package"],
              "offline_paper_order_intent_consumed_token_v75_2r.json":out["consumed_authorization_token"],
              "offline_paper_order_intent_execution_checks_v75_2r.json":{"execution_id":out["execution_id"],"execution_checks":out["execution_checks"],"execution_checks_sha256":out["execution_checks_sha256"]},
              "offline_paper_order_intent_execution_ledger_v75_2r.json":{"execution_id":out["execution_id"],"execution_ledger":out["execution_ledger"],"execution_ledger_sha256":out["execution_ledger_sha256"]}}
    for n,p in payloads.items(): (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_order_intent_execution_v75_2r.sha256").write_text(out["offline_paper_order_intent_execution_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--authorization",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--executed-at")
    a=p.parse_args(argv)
    try:
        c=read_json(Path(a.config)); out=build_execution(read_json(Path(a.authorization)),c,a.executed_at)
        write_outputs(out,Path(a.output_dir),c.get("prevent_output_overwrite",True))
        print(json.dumps({"status":out["status"],"decision":out["decision"],"execution_id":out["execution_id"],
          "execution_state":out["execution_state"],"authorization_state":out["authorization_state"],
          "order_intents_created":out["order_intents_created"],
          "order_intents":[{"order_intent_id":x["order_intent_id"],"symbol":x["symbol"],
                            "signal_action":x["signal_action"],"intent_action":x["intent_action"],
                            "quantity":x["quantity"],"reference_price":x["reference_price"]}
                           for x in out["order_intent_package"]["order_intents"]],
          "token_consumed":out["token_consumed"],"order_intent_validation_allowed":True,
          "order_generation_allowed":False,"orders_created":0,"orders_submitted":0,
          "fill_simulation_allowed":False,"network_allowed":False,"approved_for_live":False,
          "network_used":False,"offline_paper_order_intent_execution_sha256":out["offline_paper_order_intent_execution_sha256"]},indent=2,sort_keys=True))
        return 0
    except (OrderIntentExecutionError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_order_intent_execution_failed","error":str(e),
          "approved_for_live":False,"network_used":False,"order_intents_created":0,
          "orders_created":0,"orders_submitted":0,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
