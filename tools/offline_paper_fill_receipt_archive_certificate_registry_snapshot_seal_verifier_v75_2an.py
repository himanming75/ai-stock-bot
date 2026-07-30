from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2AN"
SCHEMA="v75.2an.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification.1"
SOURCE_SCHEMA="v75.2am.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal.1"
SOURCE_VERSION="75.2AM"

class OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("top-level JSON must be an object")
    return v

def validate_config(c:Dict[str,Any])->None:
    if c.get("verification_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("verification_scope invalid")
    for k in ("require_seal_integrity","require_seal_manifest_integrity","require_sealed_index_integrity",
              "require_seal_checks_integrity","require_seal_ledger_integrity","require_deterministic_seal_id",
              "require_receipt_notional_recalculation","require_zero_settlement_and_account_mutations"):
        if c.get(k) is not True: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"{k} must be true")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS": raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA or s.get("version")!=SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("unsupported source schema or version")
    if s.get("decision")!="offline_paper_fill_receipt_archive_certificate_registry_snapshot_sealed":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("source decision invalid")
    if s.get("seal_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("source seal scope invalid")
    if s.get("seal_state")!="SEALED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("source seal state invalid")

    observed=s.get("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_sha256",None)
    if observed!=sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("seal integrity failed")
    for f,h in (("seal_manifest","seal_manifest_sha256"),("sealed_index","sealed_index_sha256"),
                ("seal_checks","seal_checks_sha256"),("seal_ledger","seal_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(f)):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"{f} integrity failed")

    seal_id=s.get("fill_receipt_archive_certificate_registry_snapshot_seal_id")
    source_verification_id=s.get("fill_receipt_archive_certificate_registry_snapshot_verification_id")
    if not isinstance(seal_id,str) or not seal_id.startswith("FSS-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("seal id invalid")
    if not isinstance(source_verification_id,str) or not source_verification_id.startswith("FSV-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("snapshot verification id invalid")

    expected_id="FSS-"+hashlib.sha256(
      f"{source_verification_id}|{s.get('source_snapshot_verification_sha256')}|{s.get('sealed_at')}|{SOURCE_VERSION}".encode()
    ).hexdigest()[:16].upper()
    if seal_id!=expected_id:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("deterministic seal id mismatch")

    manifest=s.get("seal_manifest")
    expected_manifest={"seal_id":seal_id,"snapshot_verification_id":source_verification_id,
      "snapshot_id":s.get("fill_receipt_archive_certificate_registry_snapshot_id"),
      "registry_id":s.get("fill_receipt_archive_certificate_registry_id"),
      "certificate_id":s.get("fill_receipt_archive_certificate_id"),
      "receipt_batch_id":s.get("receipt_batch_id"),
      "sealed_receipt_count":s.get("sealed_receipt_count"),
      "seal_effect":"OFFLINE_FINAL_IMMUTABLE_EVIDENCE_SEAL_ONLY",
      "seal_state":"SEALED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "sealed_at":s.get("sealed_at")}
    if manifest!=expected_manifest:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("seal manifest linkage invalid")

    index=s.get("sealed_index")
    if not isinstance(index,list) or not index:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed index required")
    if s.get("sealed_receipt_count")!=len(index):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed receipt count mismatch")
    seen=set()
    for i,x in enumerate(index,1):
        if not isinstance(x,dict) or x.get("seal_index")!=i or x.get("snapshot_index")!=i or x.get("registry_index")!=i or x.get("certificate_index")!=i or x.get("archive_index")!=i:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed index sequence invalid")
        rid=x.get("receipt_id")
        if not isinstance(rid,str) or not rid.startswith("FRC-") or rid in seen:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed receipt id invalid or duplicate")
        seen.add(rid)
        for k in ("receipt_sha256","fill_id","symbol","side"):
            if not isinstance(x.get(k),str) or not x.get(k):
                raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"sealed index {k} invalid")
        q,p=x.get("filled_quantity"),x.get("fill_price")
        if isinstance(q,bool) or not isinstance(q,int) or q<=0:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed quantity invalid")
        if isinstance(p,bool) or not isinstance(p,(int,float)) or float(p)<=0:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed price invalid")
        if x.get("notional_value")!=round(float(p)*q,10):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed notional invalid")
        if x.get("seal_state")!="SEALED_VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("sealed receipt state invalid")

    checks=s.get("seal_checks"); ledger=s.get("seal_ledger")
    if not isinstance(checks,list) or len(checks)!=12:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("seal checks invalid")
    if not isinstance(ledger,list) or len(ledger)!=6:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("seal ledger invalid")
    for i,x in enumerate(checks,1):
        if x.get("check_index")!=i or x.get("state") not in {"PASS","LOCKED","ENFORCED"}:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("seal check sequence invalid")
    for i,x in enumerate(ledger,1):
        if x.get("ledger_index")!=i or x.get("seal_id")!=seal_id:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("seal ledger sequence invalid")

    gate=s.get("seal_gate",{})
    expected={"archive_certificate_registry_snapshot_sealed":True,"seal_immutable":True,
      "seal_effect":"OFFLINE_FINAL_IMMUTABLE_EVIDENCE_SEAL_ONLY","settlement_execution_allowed":False,
      "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
      "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"seal_gate {k} invalid")
    for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created","external_orders_submitted","broker_routes_created"):
        if s.get(k)!=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"mutation detected: {k}")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","approved_for_live","network_used"):
        if s.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError(f"unsafe source state: {k}")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError("safety lock invalid")
    return index

def build_verification(source:Dict[str,Any],config:Dict[str,Any])->Dict[str,Any]:
    validate_config(config); index=validate_source(source)
    verification_id="FSX-"+hashlib.sha256(
      f"{source['fill_receipt_archive_certificate_registry_snapshot_seal_id']}|"
      f"{source['offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()
    verified_index=[{"seal_index":x["seal_index"],"snapshot_index":x["snapshot_index"],"registry_index":x["registry_index"],
      "certificate_index":x["certificate_index"],"archive_index":x["archive_index"],
      "receipt_id":x["receipt_id"],"receipt_sha256":x["receipt_sha256"],"fill_id":x["fill_id"],
      "symbol":x["symbol"],"side":x["side"],"filled_quantity":x["filled_quantity"],
      "fill_price":x["fill_price"],"notional_value":x["notional_value"],
      "verification_state":"VERIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"} for x in index]
    checks=[{"check_index":i,"check":n,"state":st} for i,(n,st) in enumerate([
      ("SEAL_INTEGRITY","PASS"),("SEAL_MANIFEST_INTEGRITY","PASS"),("SEALED_INDEX_INTEGRITY","PASS"),
      ("SEAL_CHECKS_INTEGRITY","PASS"),("SEAL_LEDGER_INTEGRITY","PASS"),("SEAL_ID_DETERMINISTIC","PASS"),
      ("SEAL_MANIFEST_LINKAGES_VERIFIED","PASS"),("SEALED_RECEIPT_NOTIONALS_RECALCULATED","PASS"),
      ("SEAL_IMMUTABILITY_CONFIRMED","LOCKED"),("SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT","ENFORCED"),
      ("NETWORK_AND_BROKER_DISABLED","PASS"),("LIVE_TRADING_PROHIBITION","ENFORCED")],1)]
    ledger=[{"ledger_index":i,"event":e,"state":st,"seal_verification_id":verification_id} for i,(e,st) in enumerate([
      ("SEAL_HASH_VERIFIED","PASS"),("SEAL_MANIFEST_VERIFIED","VERIFIED"),
      ("SEALED_INDEX_VERIFIED","VERIFIED"),("SEAL_CHECKS_AND_LEDGER_VERIFIED","PASS"),
      ("SEAL_IMMUTABILITY_AND_SAFETY_CONFIRMED","ENFORCED"),
      ("OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_VERIFICATION_COMPLETED","VERIFIED")],1)]
    out={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verified",
      "fill_receipt_archive_certificate_registry_snapshot_seal_verification_id":verification_id,
      "fill_receipt_archive_certificate_registry_snapshot_seal_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_id"],
      "fill_receipt_archive_certificate_registry_snapshot_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_verification_id"],
      "fill_receipt_archive_certificate_registry_snapshot_id":source["fill_receipt_archive_certificate_registry_snapshot_id"],
      "fill_receipt_archive_certificate_registry_verification_id":source["fill_receipt_archive_certificate_registry_verification_id"],
      "fill_receipt_archive_certificate_registry_id":source["fill_receipt_archive_certificate_registry_id"],
      "fill_receipt_archive_certificate_verification_id":source["fill_receipt_archive_certificate_verification_id"],
      "fill_receipt_archive_certificate_id":source["fill_receipt_archive_certificate_id"],
      "fill_receipt_archive_verification_id":source["fill_receipt_archive_verification_id"],
      "fill_receipt_archive_package_id":source["fill_receipt_archive_package_id"],
      "fill_receipt_verification_id":source["fill_receipt_verification_id"],"receipt_batch_id":source["receipt_batch_id"],
      "verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_VERIFICATION_ONLY",
      "verification_state":"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL",
      "archive_certificate_registry_snapshot_seal_verified":True,
      "verified_sealed_receipt_count":len(verified_index),
      "verified_sealed_index":verified_index,"verified_sealed_index_sha256":sha256_of(verified_index),
      "verification_checks":checks,"verification_checks_sha256":sha256_of(checks),
      "verification_ledger":ledger,"verification_ledger_sha256":sha256_of(ledger),
      "verification_gate":{"archive_certificate_registry_snapshot_seal_verified":True,"seal_immutable":True,
        "seal_effect":"OFFLINE_FINAL_IMMUTABLE_EVIDENCE_SEAL_ONLY","settlement_execution_allowed":False,
        "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
        "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
        "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2AO"},
      "source_seal_sha256":source["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_sha256"],
      "source_seal_manifest_sha256":source["seal_manifest_sha256"],
      "source_sealed_index_sha256":source["sealed_index_sha256"],
      "source_seal_checks_sha256":source["seal_checks_sha256"],
      "source_seal_ledger_sha256":source["seal_ledger_sha256"],
      "session_id":source["session_id"],"cycle_id":source["cycle_id"],"cycle_sequence":source["cycle_sequence"],
      "champion_candidate_id":source["champion_candidate_id"],"settlements_created":0,"positions_updated":0,
      "cash_updates_created":0,"portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
      "approved_for_live":False,"network_used":False,"safety_lock":copy.deepcopy(source["safety_lock"]),
      "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_sha256"]=sha256_of(out)
    return out

def write_outputs(o:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_v75_2an.json":o,
      "offline_paper_verified_fill_receipt_archive_certificate_registry_snapshot_sealed_index_v75_2an.json":{
        "seal_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_verification_id"],
        "verified_sealed_receipt_count":o["verified_sealed_receipt_count"],
        "verified_sealed_index":o["verified_sealed_index"],"verified_sealed_index_sha256":o["verified_sealed_index_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_checks_v75_2an.json":{
        "seal_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_verification_id"],
        "verification_checks":o["verification_checks"],"verification_checks_sha256":o["verification_checks_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_ledger_v75_2an.json":{
        "seal_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_verification_id"],
        "verification_ledger":o["verification_ledger"],"verification_ledger_sha256":o["verification_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_v75_2an.sha256").write_text(
      o["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--config",required=True); p.add_argument("--output-dir",required=True)
    a=p.parse_args(argv)
    try:
        o=build_verification(read_json(Path(a.input)),read_json(Path(a.config))); write_outputs(o,Path(a.output_dir))
        print(json.dumps({k:o[k] for k in ("status","decision",
          "fill_receipt_archive_certificate_registry_snapshot_seal_verification_id","verification_state",
          "verified_sealed_receipt_count","settlements_created","positions_updated","cash_updates_created",
          "portfolio_updates_created","external_orders_submitted","broker_routes_created","network_used","approved_for_live",
          "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_sha256")},indent=2,sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealVerificationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL",
          "decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_verification_failed",
          "error":str(e),"settlements_created":0,"positions_updated":0,"cash_updates_created":0,
          "portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
          "network_used":False,"approved_for_live":False,"version":VERSION},indent=2,sort_keys=True))
        return 1
if __name__=="__main__": raise SystemExit(main())
