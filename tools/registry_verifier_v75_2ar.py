from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2AR"
SCHEMA="v75.2ar.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification.1"
SOURCE_SCHEMA="v75.2aq.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry.1"
SOURCE_VERSION="75.2AQ"

class RegistryVerificationError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try:
        v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise RegistryVerificationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise RegistryVerificationError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict):
        raise RegistryVerificationError("top-level JSON must be an object")
    return v

def validate_config(c:Dict[str,Any])->None:
    if c.get("verification_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_VERIFICATION_ONLY":
        raise RegistryVerificationError("verification_scope invalid")
    for k in ("require_registry_integrity","require_registry_manifest_integrity","require_registered_index_integrity",
              "require_registry_checks_integrity","require_registry_ledger_integrity",
              "require_deterministic_registry_id","require_receipt_notional_recalculation",
              "require_zero_settlement_and_account_mutations"):
        if c.get(k) is not True:
            raise RegistryVerificationError(f"{k} must be true")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False:
            raise RegistryVerificationError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS":
        raise RegistryVerificationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA or s.get("version")!=SOURCE_VERSION:
        raise RegistryVerificationError("unsupported source schema or version")
    if s.get("decision")!="offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registered":
        raise RegistryVerificationError("source decision invalid")
    if s.get("registry_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_ONLY":
        raise RegistryVerificationError("source registry scope invalid")
    if s.get("registry_state")!="REGISTERED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE":
        raise RegistryVerificationError("source registry state invalid")

    observed=s.get("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256")
    clone=copy.deepcopy(s)
    clone.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256",None)
    if observed!=sha256_of(clone):
        raise RegistryVerificationError("registry integrity failed")

    for field,hfield in (
        ("registry_manifest","registry_manifest_sha256"),
        ("registered_index","registered_index_sha256"),
        ("registry_checks","registry_checks_sha256"),
        ("registry_ledger","registry_ledger_sha256")):
        if s.get(hfield)!=sha256_of(s.get(field)):
            raise RegistryVerificationError(f"{field} integrity failed")

    rid=s.get("fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id")
    vid=s.get("fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id")
    if not isinstance(rid,str) or not rid.startswith("FCRS-"):
        raise RegistryVerificationError("registry id invalid")
    if not isinstance(vid,str) or not vid.startswith("FCX-"):
        raise RegistryVerificationError("certificate verification id invalid")

    manifest=s.get("registry_manifest")
    if not isinstance(manifest,dict):
        raise RegistryVerificationError("registry manifest invalid")
    expected_id="FCRS-"+hashlib.sha256(
      f"{vid}|{s['source_certificate_verification_sha256']}|{s['registered_at']}|75.2AQ".encode()
    ).hexdigest()[:16].upper()
    if rid!=expected_id or manifest.get("registry_id")!=rid:
        raise RegistryVerificationError("deterministic registry id mismatch")
    if manifest.get("registered_receipt_count")!=s.get("registered_receipt_count"):
        raise RegistryVerificationError("manifest receipt count mismatch")
    if manifest.get("registry_effect")!="OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRATION_ONLY":
        raise RegistryVerificationError("registry effect invalid")

    index=s.get("registered_index")
    if not isinstance(index,list) or not index:
        raise RegistryVerificationError("registered index required")
    if s.get("registered_receipt_count")!=len(index):
        raise RegistryVerificationError("registered receipt count mismatch")
    seen=set()
    for i,x in enumerate(index,1):
        if not isinstance(x,dict) or x.get("registry_record_index")!=i:
            raise RegistryVerificationError("registry record sequence invalid")
        rid2=x.get("receipt_id")
        if not isinstance(rid2,str) or not rid2.startswith("FRC-") or rid2 in seen:
            raise RegistryVerificationError("receipt id invalid or duplicate")
        seen.add(rid2)
        q,p=x.get("filled_quantity"),x.get("fill_price")
        if isinstance(q,bool) or not isinstance(q,int) or q<=0:
            raise RegistryVerificationError("quantity invalid")
        if isinstance(p,bool) or not isinstance(p,(int,float)) or float(p)<=0:
            raise RegistryVerificationError("price invalid")
        if x.get("notional_value")!=round(float(p)*q,10):
            raise RegistryVerificationError("notional invalid")
        if x.get("registry_state")!="REGISTERED_VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise RegistryVerificationError("registered receipt state invalid")

    if len(s.get("registry_checks",[]))!=12 or len(s.get("registry_ledger",[]))!=6:
        raise RegistryVerificationError("registry checks or ledger invalid")

    gate=s.get("registry_gate",{})
    expected={"archive_certificate_registry_snapshot_seal_certificate_registered":True,
      "registry_immutable":True,"registry_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRATION_ONLY",
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,
      "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v:
            raise RegistryVerificationError(f"registry_gate {k} invalid")

    for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created",
              "external_orders_submitted","broker_routes_created"):
        if s.get(k)!=0:
            raise RegistryVerificationError(f"mutation detected: {k}")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","approved_for_live","network_used"):
        if s.get(k) is not False:
            raise RegistryVerificationError(f"unsafe source state: {k}")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise RegistryVerificationError("safety lock invalid")
    return index

def verify_registry(source:Dict[str,Any],config:Dict[str,Any])->Dict[str,Any]:
    validate_config(config)
    index=validate_source(source)
    verification_id="FCRX-"+hashlib.sha256(
      f"{source['fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id']}|"
      f"{source['offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    verified=[dict(x,verification_state=
      "VERIFIED_REGISTERED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT")
      for x in index]

    checks=[{"check_index":i,"check":name,"state":state} for i,(name,state) in enumerate([
      ("REGISTRY_INTEGRITY","PASS"),("REGISTRY_MANIFEST_INTEGRITY","PASS"),
      ("REGISTERED_INDEX_INTEGRITY","PASS"),("REGISTRY_CHECKS_INTEGRITY","PASS"),
      ("REGISTRY_LEDGER_INTEGRITY","PASS"),("REGISTRY_ID_DETERMINISTIC","PASS"),
      ("RECEIPT_LINKAGES_PRESERVED","PASS"),("RECEIPT_NOTIONALS_RECALCULATED","PASS"),
      ("REGISTRY_IMMUTABILITY_CONFIRMED","LOCKED"),
      ("SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT","ENFORCED"),
      ("NETWORK_AND_BROKER_DISABLED","PASS"),("LIVE_TRADING_PROHIBITION","ENFORCED")],1)]

    ledger=[{"ledger_index":i,"event":event,"state":state,
      "registry_verification_id":verification_id} for i,(event,state) in enumerate([
      ("REGISTRY_ACCEPTED","PASS"),("REGISTRY_HASH_VERIFIED","VERIFIED"),
      ("REGISTRY_MANIFEST_AND_INDEX_VERIFIED","VERIFIED"),
      ("REGISTRY_CHECKS_AND_LEDGER_VERIFIED","VERIFIED"),
      ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT","ENFORCED"),
      ("OFFLINE_CERTIFICATE_REGISTRY_VERIFICATION_COMPLETED","VERIFIED")],1)]

    out={"status":"PASS",
      "decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verified",
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id":verification_id,
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id":
        source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id"],
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id":
        source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id"],
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id":
        source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id"],
      "receipt_batch_id":source["receipt_batch_id"],
      "verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_VERIFICATION_ONLY",
      "verification_state":"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY",
      "archive_certificate_registry_snapshot_seal_certificate_registry_verified":True,
      "verified_registered_receipt_count":len(verified),
      "verified_registered_index":verified,
      "verified_registered_index_sha256":sha256_of(verified),
      "verification_checks":checks,"verification_checks_sha256":sha256_of(checks),
      "verification_ledger":ledger,"verification_ledger_sha256":sha256_of(ledger),
      "verification_gate":{"archive_certificate_registry_snapshot_seal_certificate_registry_verified":True,
        "registry_immutable":True,
        "registry_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_VERIFICATION_ONLY",
        "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
        "portfolio_update_allowed":False,"external_order_submission_allowed":False,
        "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
        "network_allowed":False,"next_version":"75.2AS"},
      "source_registry_sha256":
        source["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256"],
      "source_registry_manifest_sha256":source["registry_manifest_sha256"],
      "source_registered_index_sha256":source["registered_index_sha256"],
      "source_registry_checks_sha256":source["registry_checks_sha256"],
      "source_registry_ledger_sha256":source["registry_ledger_sha256"],
      "session_id":source["session_id"],"cycle_id":source["cycle_id"],
      "cycle_sequence":source["cycle_sequence"],"champion_candidate_id":source["champion_candidate_id"],
      "settlements_created":0,"positions_updated":0,"cash_updates_created":0,
      "portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,
      "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"broker_connection_allowed":False,"approved_for_live":False,
      "network_used":False,"safety_lock":copy.deepcopy(source["safety_lock"]),
      "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256"]=sha256_of(out)
    return out

def write_outputs(o:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_v75_2ar.json":o,
      "offline_paper_verified_registered_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_index_v75_2ar.json":{
        "registry_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id"],
        "verified_registered_receipt_count":o["verified_registered_receipt_count"],
        "verified_registered_index":o["verified_registered_index"],
        "verified_registered_index_sha256":o["verified_registered_index_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_checks_v75_2ar.json":{
        "registry_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id"],
        "verification_checks":o["verification_checks"],
        "verification_checks_sha256":o["verification_checks_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_ledger_v75_2ar.json":{
        "registry_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id"],
        "verification_ledger":o["verification_ledger"],
        "verification_ledger_sha256":o["verification_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_v75_2ar.sha256").write_text(
      o["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256"]+"\n",
      encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True)
    a=p.parse_args(argv)
    try:
        o=verify_registry(read_json(Path(a.input)),read_json(Path(a.config)))
        write_outputs(o,Path(a.output_dir))
        keys=("status","decision",
          "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id",
          "verification_state","verified_registered_receipt_count","settlements_created","positions_updated",
          "cash_updates_created","portfolio_updates_created","external_orders_submitted",
          "broker_routes_created","network_used","approved_for_live",
          "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256")
        print(json.dumps({k:o[k] for k in keys},indent=2,sort_keys=True))
        return 0
    except (RegistryVerificationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL",
          "decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_failed",
          "error":str(e),"settlements_created":0,"positions_updated":0,
          "cash_updates_created":0,"portfolio_updates_created":0,
          "external_orders_submitted":0,"broker_routes_created":0,
          "network_used":False,"approved_for_live":False,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
