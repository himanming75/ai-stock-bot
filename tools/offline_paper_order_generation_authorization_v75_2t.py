from __future__ import annotations
import argparse, copy, hashlib, json, secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2T"
SCHEMA="v75.2t.offline_paper_order_generation_authorization.1"
SOURCE_SCHEMA="v75.2s.offline_paper_order_intent_validation.1"

class OrderGenerationAuthorizationError(ValueError): pass

def canonical_json(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(x:Any)->str:
    return hashlib.sha256(canonical_json(x).encode("utf-8")).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: x=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OrderGenerationAuthorizationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OrderGenerationAuthorizationError(f"invalid JSON: {path}") from e
    if not isinstance(x,dict): raise OrderGenerationAuthorizationError("top-level JSON must be an object")
    return x

def parse_ts(v:Any,name:str)->datetime:
    if not isinstance(v,str) or not v: raise OrderGenerationAuthorizationError(f"{name} invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OrderGenerationAuthorizationError(f"{name} must be ISO-8601") from e
    if d.tzinfo is None: raise OrderGenerationAuthorizationError(f"{name} must include timezone")
    return d

def validate_config(c:Dict[str,Any])->int:
    ttl=c.get("authorization_ttl_seconds")
    if isinstance(ttl,bool) or not isinstance(ttl,int) or not (60<=ttl<=3600):
        raise OrderGenerationAuthorizationError("authorization_ttl_seconds must be 60..3600")
    if c.get("authorization_scope")!="OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY":
        raise OrderGenerationAuthorizationError("authorization_scope invalid")
    for k in ("require_source_integrity","require_validated_order_intents","require_intent_identity_lock",
              "require_single_use_token","require_zero_orders","require_safety_lock"):
        if c.get(k) is not True: raise OrderGenerationAuthorizationError(f"{k} must be true")
    for k in ("order_object_creation_allowed","order_submission_allowed","fill_simulation_allowed",
              "paper_orders_allowed","live_orders_allowed","network_allowed","broker_connection_allowed",
              "external_side_effects_allowed"):
        if c.get(k) is not False: raise OrderGenerationAuthorizationError(f"{k} must be false")
    return ttl

def validate_source(s:Dict[str,Any])->None:
    if s.get("status")!="PASS": raise OrderGenerationAuthorizationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA: raise OrderGenerationAuthorizationError("unsupported source schema")
    if s.get("validation_state")!="READY_FOR_ORDER_GENERATION_AUTHORIZATION":
        raise OrderGenerationAuthorizationError("source not ready")
    observed=s.get("offline_paper_order_intent_validation_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_order_intent_validation_sha256",None)
    if observed!=sha256_of(clone): raise OrderGenerationAuthorizationError("source integrity failed")
    for f,h in (("validation_checks","validation_checks_sha256"),
                ("validation_ledger","validation_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(f)): raise OrderGenerationAuthorizationError(f"{f} integrity failed")
    gate=s.get("validation_gate",{})
    expected={"order_intent_validated":True,"order_generation_authorization_allowed":True,
              "order_generation_allowed":False,"fill_simulation_allowed":False,
              "paper_orders_allowed":False,"live_orders_allowed":False,
              "network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OrderGenerationAuthorizationError(f"validation_gate {k} invalid")
    intents=s.get("validated_order_intents")
    summary=s.get("validated_order_intent_summary")
    if not isinstance(intents,list) or not intents: raise OrderGenerationAuthorizationError("validated order intents required")
    if not isinstance(summary,dict) or summary.get("order_intent_count")!=len(intents):
        raise OrderGenerationAuthorizationError("intent summary mismatch")
    ids=set()
    for x in intents:
        iid=x.get("order_intent_id")
        if not isinstance(iid,str) or not iid.startswith("INT-"): raise OrderGenerationAuthorizationError("invalid order_intent_id")
        if iid in ids: raise OrderGenerationAuthorizationError("duplicate order_intent_id")
        ids.add(iid)
        if x.get("intent_action") not in ("BUY","SELL","NO_ACTION"):
            raise OrderGenerationAuthorizationError("invalid intent action")
        if x.get("order_created") is not False or x.get("order_submitted") is not False:
            raise OrderGenerationAuthorizationError("order side effect detected")
        if x.get("fill_simulated") is not False or x.get("broker_routed") is not False or x.get("network_used") is not False:
            raise OrderGenerationAuthorizationError("unsafe intent side effect")
    for k in ("order_generation_allowed","fill_simulation_allowed","paper_orders_allowed",
              "live_orders_allowed","network_allowed","broker_connection_allowed"):
        if s.get(k) is not False: raise OrderGenerationAuthorizationError(f"{k} must be false")
    if s.get("orders_created")!=0 or s.get("orders_submitted")!=0:
        raise OrderGenerationAuthorizationError("orders already created/submitted")
    if s.get("approved_for_live") is not False or s.get("network_used") is not False:
        raise OrderGenerationAuthorizationError("safety violation")
    lock=s.get("safety_lock")
    if not isinstance(lock,dict) or lock.get("lock_state")!="ENFORCED":
        raise OrderGenerationAuthorizationError("safety lock invalid")

def authorization_id(validation_id:str,issued_at:str)->str:
    return "OGA-"+hashlib.sha256(f"{validation_id}|{issued_at}|{VERSION}".encode()).hexdigest()[:16].upper()

def build_authorization(source:Dict[str,Any],config:Dict[str,Any],issued_at:Optional[str]=None,nonce:Optional[str]=None)->Dict[str,Any]:
    validate_source(source); ttl=validate_config(config)
    issued=datetime.now(timezone.utc).replace(microsecond=0) if issued_at is None else parse_ts(issued_at,"issued_at")
    expires=issued+timedelta(seconds=ttl)
    issued_s=issued.isoformat(); expires_s=expires.isoformat()
    aid=authorization_id(source["validation_id"],issued_s)
    eligible=[x for x in source["validated_order_intents"] if x["intent_action"] in ("BUY","SELL")]
    if not eligible: raise OrderGenerationAuthorizationError("no actionable order intents")
    manifest=[{"order_intent_id":x["order_intent_id"],"symbol":x["symbol"],"side":x["intent_action"],
               "quantity":x["quantity"],"reference_price":x["reference_price"],
               "order_object_creation_authorized":True,"order_created":False,"order_submitted":False}
              for x in eligible]
    token_material={"authorization_id":aid,"validation_id":source["validation_id"],
                    "issued_at":issued_s,"expires_at":expires_s,"nonce":nonce or secrets.token_hex(16),
                    "scope":"OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY",
                    "authorized_order_intent_ids":[x["order_intent_id"] for x in manifest]}
    token={**token_material,"token_sha256":sha256_of(token_material),"single_use":True,
           "consumed":False,"consumed_at":None,"token_state":"ISSUED_NOT_CONSUMED"}
    checks=[
      {"check_index":1,"check":"ORDER_INTENT_VALIDATION_INTEGRITY","state":"PASS"},
      {"check_index":2,"check":"VALIDATED_ORDER_INTENT_MANIFEST","state":"PASS"},
      {"check_index":3,"check":"ORDER_INTENT_IDENTITY_LOCK","state":"LOCKED"},
      {"check_index":4,"check":"ORDER_OBJECT_CREATION_NOT_STARTED","state":"PASS"},
      {"check_index":5,"check":"ORDER_SUBMISSION_NOT_STARTED","state":"PASS"},
      {"check_index":6,"check":"FILL_SIMULATION_NOT_STARTED","state":"PASS"},
      {"check_index":7,"check":"ZERO_ORDER_SIDE_EFFECTS","state":"PASS"},
      {"check_index":8,"check":"NETWORK_DISABLED","state":"PASS"},
      {"check_index":9,"check":"BROKER_DISCONNECTED","state":"PASS"},
      {"check_index":10,"check":"SINGLE_USE_TOKEN_POLICY","state":"ENFORCED"},
      {"check_index":11,"check":"AUTHORIZATION_SCOPE_LIMIT","state":"ENFORCED"},
      {"check_index":12,"check":"LIVE_TRADING_PROHIBITION","state":"ENFORCED"}]
    ledger=[
      {"ledger_index":1,"event":"ORDER_INTENT_VALIDATION_VERIFIED","state":"PASS","authorization_id":aid},
      {"ledger_index":2,"event":"ORDER_INTENT_IDENTITIES_LOCKED","state":"LOCKED","authorization_id":aid},
      {"ledger_index":3,"event":"ORDER_OBJECT_CREATION_SCOPE_AUTHORIZED","state":"AUTHORIZED","authorization_id":aid},
      {"ledger_index":4,"event":"SINGLE_USE_TOKEN_ISSUED","state":"ISSUED_NOT_CONSUMED","authorization_id":aid},
      {"ledger_index":5,"event":"SAFETY_LOCKS_RECONFIRMED","state":"ENFORCED","authorization_id":aid},
      {"ledger_index":6,"event":"ORDER_GENERATION_AUTHORIZATION_COMPLETED","state":"AUTHORIZED_NOT_EXECUTED","authorization_id":aid}]
    out={"status":"PASS","decision":"offline_paper_order_generation_authorized",
         "authorization_id":aid,"authorization_scope":"OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY",
         "authorization_state":"AUTHORIZED_NOT_EXECUTED",
         "order_generation_authorized":True,"order_generation_executed":False,
         "order_objects_created":0,"token_consumed":False,
         "authorization_token":token,"authorization_token_sha256":sha256_of(token),
         "authorized_order_intent_manifest":manifest,
         "authorized_order_intent_manifest_sha256":sha256_of(manifest),
         "authorization_checks":checks,"authorization_checks_sha256":sha256_of(checks),
         "authorization_ledger":ledger,"authorization_ledger_sha256":sha256_of(ledger),
         "source_order_intent_validation_sha256":source["offline_paper_order_intent_validation_sha256"],
         "source_order_intent_execution_sha256":source["source_order_intent_execution_sha256"],
         "source_order_intent_package_sha256":source["source_order_intent_package_sha256"],
         "validation_id":source["validation_id"],"execution_id":source["execution_id"],
         "session_id":source["session_id"],"cycle_id":source["cycle_id"],
         "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
         "authorization_gate":{"order_generation_authorized":True,
                               "order_object_creation_execution_allowed":True,
                               "order_object_creation_allowed":False,
                               "order_submission_allowed":False,
                               "fill_simulation_allowed":False,
                               "paper_orders_allowed":False,
                               "live_orders_allowed":False,
                               "network_allowed":False,
                               "next_version":"75.2U"},
         "order_submission_allowed":False,"fill_simulation_allowed":False,
         "paper_orders_allowed":False,"live_orders_allowed":False,
         "network_allowed":False,"broker_connection_allowed":False,
         "orders_created":0,"orders_submitted":0,"approved_for_live":False,"network_used":False,
         "safety_lock":copy.deepcopy(source["safety_lock"]),
         "issued_at":issued_s,"expires_at":expires_s,"authorization_ttl_seconds":ttl,
         "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_order_generation_authorization_sha256"]=sha256_of(out)
    return out

def write_outputs(out:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={"offline_paper_order_generation_authorization_v75_2t.json":out,
              "offline_paper_order_generation_authorization_token_v75_2t.json":out["authorization_token"],
              "offline_paper_authorized_order_intents_v75_2t.json":{"authorization_id":out["authorization_id"],"authorized_order_intent_manifest":out["authorized_order_intent_manifest"],"authorized_order_intent_manifest_sha256":out["authorized_order_intent_manifest_sha256"]},
              "offline_paper_order_generation_authorization_checks_v75_2t.json":{"authorization_id":out["authorization_id"],"authorization_checks":out["authorization_checks"],"authorization_checks_sha256":out["authorization_checks_sha256"]},
              "offline_paper_order_generation_authorization_ledger_v75_2t.json":{"authorization_id":out["authorization_id"],"authorization_ledger":out["authorization_ledger"],"authorization_ledger_sha256":out["authorization_ledger_sha256"]}}
    for n,p in payloads.items(): (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_order_generation_authorization_v75_2t.sha256").write_text(out["offline_paper_order_generation_authorization_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--issued-at"); p.add_argument("--nonce")
    a=p.parse_args(argv)
    try:
        out=build_authorization(read_json(Path(a.input)),read_json(Path(a.config)),a.issued_at,a.nonce)
        write_outputs(out,Path(a.output_dir))
        first=out["authorized_order_intent_manifest"][0]
        print(json.dumps({"status":out["status"],"decision":out["decision"],
          "authorization_id":out["authorization_id"],"authorization_state":out["authorization_state"],
          "authorization_scope":out["authorization_scope"],
          "authorized_order_intent_count":len(out["authorized_order_intent_manifest"]),
          "first_authorized_order_intent":first,
          "order_generation_authorized":out["order_generation_authorized"],
          "order_generation_executed":out["order_generation_executed"],
          "order_object_creation_execution_allowed":True,
          "order_object_creation_allowed":False,
          "token_state":out["authorization_token"]["token_state"],
          "token_consumed":False,"orders_created":0,"orders_submitted":0,
          "network_allowed":False,"approved_for_live":False,"network_used":False,
          "offline_paper_order_generation_authorization_sha256":out["offline_paper_order_generation_authorization_sha256"]},indent=2,sort_keys=True))
        return 0
    except (OrderGenerationAuthorizationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_order_generation_authorization_failed",
          "error":str(e),"approved_for_live":False,"network_used":False,
          "orders_created":0,"orders_submitted":0,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__": raise SystemExit(main())
