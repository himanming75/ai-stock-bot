from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2AL"
SCHEMA="v75.2al.offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification.1"
SOURCE_SCHEMA="v75.2ak.offline_paper_fill_receipt_archive_certificate_registry_snapshot.1"
SOURCE_VERSION="75.2AK"

class OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("top-level JSON must be an object")
    return v

def validate_config(c:Dict[str,Any])->None:
    if c.get("verification_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("verification_scope invalid")
    for k in ("require_snapshot_integrity","require_snapshot_manifest_integrity","require_snapshot_index_integrity",
              "require_snapshot_checks_integrity","require_snapshot_ledger_integrity","require_deterministic_snapshot_id",
              "require_receipt_notional_recalculation","require_zero_settlement_and_account_mutations"):
        if c.get(k) is not True: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"{k} must be true")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS": raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA or s.get("version")!=SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("unsupported source schema or version")
    if s.get("decision")!="offline_paper_fill_receipt_archive_certificate_registry_snapshot_created":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("source decision invalid")
    if s.get("snapshot_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("source snapshot scope invalid")
    if s.get("snapshot_state")!="SEALED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("source snapshot state invalid")

    observed=s.get("offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256",None)
    if observed!=sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot integrity failed")
    for f,h in (("snapshot_manifest","snapshot_manifest_sha256"),("snapshot_index","snapshot_index_sha256"),
                ("snapshot_checks","snapshot_checks_sha256"),("snapshot_ledger","snapshot_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(f)):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"{f} integrity failed")

    sid=s.get("fill_receipt_archive_certificate_registry_snapshot_id")
    rvid=s.get("fill_receipt_archive_certificate_registry_verification_id")
    if not isinstance(sid,str) or not sid.startswith("FRS-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot id invalid")
    if not isinstance(rvid,str) or not rvid.startswith("FRV-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("registry verification id invalid")

    expected_id="FRS-"+hashlib.sha256(
        f"{rvid}|{s.get('source_registry_verification_sha256')}|{s.get('snapshotted_at')}|{SOURCE_VERSION}".encode()
    ).hexdigest()[:16].upper()
    if sid!=expected_id:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("deterministic snapshot id mismatch")

    manifest=s.get("snapshot_manifest")
    expected_manifest={"snapshot_id":sid,"registry_verification_id":rvid,
      "registry_id":s.get("fill_receipt_archive_certificate_registry_id"),
      "certificate_id":s.get("fill_receipt_archive_certificate_id"),
      "receipt_batch_id":s.get("receipt_batch_id"),
      "snapshotted_receipt_count":s.get("snapshotted_receipt_count"),
      "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY",
      "snapshot_state":"SEALED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "snapshotted_at":s.get("snapshotted_at")}
    if manifest!=expected_manifest:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot manifest linkage invalid")

    index=s.get("snapshot_index")
    if not isinstance(index,list) or not index:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot index required")
    if s.get("snapshotted_receipt_count")!=len(index):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot receipt count mismatch")
    seen=set()
    for i,x in enumerate(index,1):
        if not isinstance(x,dict) or x.get("snapshot_index")!=i or x.get("registry_index")!=i or x.get("certificate_index")!=i or x.get("archive_index")!=i:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot index sequence invalid")
        rid=x.get("receipt_id")
        if not isinstance(rid,str) or not rid.startswith("FRC-") or rid in seen:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot receipt id invalid or duplicate")
        seen.add(rid)
        for k in ("receipt_sha256","fill_id","symbol","side"):
            if not isinstance(x.get(k),str) or not x.get(k):
                raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"snapshot index {k} invalid")
        q,p=x.get("filled_quantity"),x.get("fill_price")
        if isinstance(q,bool) or not isinstance(q,int) or q<=0:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot quantity invalid")
        if isinstance(p,bool) or not isinstance(p,(int,float)) or float(p)<=0:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot price invalid")
        if x.get("notional_value")!=round(float(p)*q,10):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot notional invalid")
        if x.get("snapshot_state")!="SNAPSHOTTED_VERIFIED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot receipt state invalid")

    checks=s.get("snapshot_checks"); ledger=s.get("snapshot_ledger")
    if not isinstance(checks,list) or len(checks)!=12:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot checks invalid")
    if not isinstance(ledger,list) or len(ledger)!=6:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot ledger invalid")
    for i,x in enumerate(checks,1):
        if x.get("check_index")!=i or x.get("state") not in {"PASS","LOCKED","ENFORCED"}:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot check sequence invalid")
    for i,x in enumerate(ledger,1):
        if x.get("ledger_index")!=i or x.get("snapshot_id")!=sid:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("snapshot ledger sequence invalid")

    gate=s.get("snapshot_gate",{})
    expected={"archive_certificate_registry_snapshot_created":True,"snapshot_immutable":True,
      "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY","settlement_execution_allowed":False,
      "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
      "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"snapshot_gate {k} invalid")
    for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created","external_orders_submitted","broker_routes_created"):
        if s.get(k)!=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"mutation detected: {k}")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","approved_for_live","network_used"):
        if s.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError(f"unsafe source state: {k}")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError("safety lock invalid")
    return index

def build_verification(source:Dict[str,Any],config:Dict[str,Any])->Dict[str,Any]:
    validate_config(config); index=validate_source(source)
    verification_id="FSV-"+hashlib.sha256(
      f"{source['fill_receipt_archive_certificate_registry_snapshot_id']}|"
      f"{source['offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()
    verified_index=[{"snapshot_index":x["snapshot_index"],"registry_index":x["registry_index"],
      "certificate_index":x["certificate_index"],"archive_index":x["archive_index"],
      "receipt_id":x["receipt_id"],"receipt_sha256":x["receipt_sha256"],"fill_id":x["fill_id"],
      "symbol":x["symbol"],"side":x["side"],"filled_quantity":x["filled_quantity"],
      "fill_price":x["fill_price"],"notional_value":x["notional_value"],
      "verification_state":"VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"} for x in index]
    checks=[{"check_index":i,"check":n,"state":st} for i,(n,st) in enumerate([
      ("SNAPSHOT_INTEGRITY","PASS"),("SNAPSHOT_MANIFEST_INTEGRITY","PASS"),
      ("SNAPSHOT_INDEX_INTEGRITY","PASS"),("SNAPSHOT_CHECKS_INTEGRITY","PASS"),
      ("SNAPSHOT_LEDGER_INTEGRITY","PASS"),("SNAPSHOT_ID_DETERMINISTIC","PASS"),
      ("SNAPSHOT_MANIFEST_LINKAGES_VERIFIED","PASS"),("SNAPSHOT_RECEIPT_NOTIONALS_RECALCULATED","PASS"),
      ("SNAPSHOT_IMMUTABILITY_CONFIRMED","LOCKED"),("SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT","ENFORCED"),
      ("NETWORK_AND_BROKER_DISABLED","PASS"),("LIVE_TRADING_PROHIBITION","ENFORCED")],1)]
    ledger=[{"ledger_index":i,"event":e,"state":st,"snapshot_verification_id":verification_id} for i,(e,st) in enumerate([
      ("SNAPSHOT_HASH_VERIFIED","PASS"),("SNAPSHOT_MANIFEST_VERIFIED","VERIFIED"),
      ("SNAPSHOT_INDEX_VERIFIED","VERIFIED"),("SNAPSHOT_CHECKS_AND_LEDGER_VERIFIED","PASS"),
      ("SNAPSHOT_IMMUTABILITY_AND_SAFETY_CONFIRMED","ENFORCED"),
      ("OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_COMPLETED","VERIFIED")],1)]
    out={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_verified",
      "fill_receipt_archive_certificate_registry_snapshot_verification_id":verification_id,
      "fill_receipt_archive_certificate_registry_snapshot_id":source["fill_receipt_archive_certificate_registry_snapshot_id"],
      "fill_receipt_archive_certificate_registry_verification_id":source["fill_receipt_archive_certificate_registry_verification_id"],
      "fill_receipt_archive_certificate_registry_id":source["fill_receipt_archive_certificate_registry_id"],
      "fill_receipt_archive_certificate_verification_id":source["fill_receipt_archive_certificate_verification_id"],
      "fill_receipt_archive_certificate_id":source["fill_receipt_archive_certificate_id"],
      "fill_receipt_archive_verification_id":source["fill_receipt_archive_verification_id"],
      "fill_receipt_archive_package_id":source["fill_receipt_archive_package_id"],
      "fill_receipt_verification_id":source["fill_receipt_verification_id"],"receipt_batch_id":source["receipt_batch_id"],
      "verification_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY",
      "verification_state":"VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "archive_certificate_registry_snapshot_verified":True,
      "verified_snapshotted_receipt_count":len(verified_index),
      "verified_snapshot_index":verified_index,"verified_snapshot_index_sha256":sha256_of(verified_index),
      "verification_checks":checks,"verification_checks_sha256":sha256_of(checks),
      "verification_ledger":ledger,"verification_ledger_sha256":sha256_of(ledger),
      "verification_gate":{"archive_certificate_registry_snapshot_verified":True,"snapshot_immutable":True,
        "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY","settlement_execution_allowed":False,
        "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
        "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
        "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2AM"},
      "source_snapshot_sha256":source["offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256"],
      "source_snapshot_manifest_sha256":source["snapshot_manifest_sha256"],
      "source_snapshot_index_sha256":source["snapshot_index_sha256"],
      "source_snapshot_checks_sha256":source["snapshot_checks_sha256"],
      "source_snapshot_ledger_sha256":source["snapshot_ledger_sha256"],
      "session_id":source["session_id"],"cycle_id":source["cycle_id"],"cycle_sequence":source["cycle_sequence"],
      "champion_candidate_id":source["champion_candidate_id"],"settlements_created":0,"positions_updated":0,
      "cash_updates_created":0,"portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
      "approved_for_live":False,"network_used":False,"safety_lock":copy.deepcopy(source["safety_lock"]),
      "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256"]=sha256_of(out)
    return out

def write_outputs(o:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_v75_2al.json":o,
      "offline_paper_verified_fill_receipt_archive_certificate_registry_snapshot_index_v75_2al.json":{
        "snapshot_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_verification_id"],
        "verified_snapshotted_receipt_count":o["verified_snapshotted_receipt_count"],
        "verified_snapshot_index":o["verified_snapshot_index"],
        "verified_snapshot_index_sha256":o["verified_snapshot_index_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_checks_v75_2al.json":{
        "snapshot_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_verification_id"],
        "verification_checks":o["verification_checks"],"verification_checks_sha256":o["verification_checks_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_ledger_v75_2al.json":{
        "snapshot_verification_id":o["fill_receipt_archive_certificate_registry_snapshot_verification_id"],
        "verification_ledger":o["verification_ledger"],"verification_ledger_sha256":o["verification_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_v75_2al.sha256").write_text(
      o["offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--config",required=True); p.add_argument("--output-dir",required=True)
    a=p.parse_args(argv)
    try:
        o=build_verification(read_json(Path(a.input)),read_json(Path(a.config))); write_outputs(o,Path(a.output_dir))
        print(json.dumps({k:o[k] for k in ("status","decision",
          "fill_receipt_archive_certificate_registry_snapshot_verification_id","verification_state",
          "verified_snapshotted_receipt_count","settlements_created","positions_updated","cash_updates_created",
          "portfolio_updates_created","external_orders_submitted","broker_routes_created","network_used","approved_for_live",
          "offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256")},indent=2,sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotVerificationError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL",
          "decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_failed",
          "error":str(e),"settlements_created":0,"positions_updated":0,"cash_updates_created":0,
          "portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
          "network_used":False,"approved_for_live":False,"version":VERSION},indent=2,sort_keys=True))
        return 1
if __name__=="__main__": raise SystemExit(main())
