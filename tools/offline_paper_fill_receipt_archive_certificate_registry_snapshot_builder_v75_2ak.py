from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2AK"
SCHEMA="v75.2ak.offline_paper_fill_receipt_archive_certificate_registry_snapshot.1"
SOURCE_SCHEMA="v75.2aj.offline_paper_fill_receipt_archive_certificate_registry_verification.1"
SOURCE_VERSION="75.2AJ"

class OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("top-level JSON must be an object")
    return v

def parse_ts(v:str)->str:
    if not isinstance(v,str) or not v: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("snapshotted_at invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("snapshotted_at must be ISO-8601") from e
    if d.tzinfo is None: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("snapshotted_at must include timezone")
    return d.isoformat()

def validate_config(c:Dict[str,Any])->None:
    if c.get("snapshot_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("snapshot_scope invalid")
    for k in ("require_registry_verification_integrity","require_verified_registry_index_integrity",
              "require_verification_checks_integrity","require_verification_ledger_integrity",
              "require_zero_settlement_and_account_mutations","create_snapshot_manifest",
              "create_snapshot_index","create_snapshot_checks","create_snapshot_ledger"):
        if c.get(k) is not True: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"{k} must be true")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS": raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA or s.get("version")!=SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("unsupported source schema or version")
    if s.get("decision")!="offline_paper_fill_receipt_archive_certificate_registry_verified":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("source decision invalid")
    if s.get("verification_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("source verification scope invalid")
    if s.get("verification_state")!="VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY" or s.get("archive_certificate_registry_verified") is not True:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("registry verification incomplete")

    observed=s.get("offline_paper_fill_receipt_archive_certificate_registry_verification_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_fill_receipt_archive_certificate_registry_verification_sha256",None)
    if observed!=sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("registry verification integrity failed")
    for f,h in (("verified_registry_index","verified_registry_index_sha256"),
                ("verification_checks","verification_checks_sha256"),("verification_ledger","verification_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(f)):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"{f} integrity failed")

    rvid=s.get("fill_receipt_archive_certificate_registry_verification_id")
    rid=s.get("fill_receipt_archive_certificate_registry_id")
    if not isinstance(rvid,str) or not rvid.startswith("FRV-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("registry verification id invalid")
    if not isinstance(rid,str) or not rid.startswith("FCR-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("registry id invalid")

    index=s.get("verified_registry_index")
    if not isinstance(index,list) or not index:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("verified registry index required")
    if s.get("verified_registered_receipt_count")!=len(index):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("verified receipt count mismatch")
    seen=set()
    for i,x in enumerate(index,1):
        if not isinstance(x,dict) or x.get("registry_index")!=i or x.get("certificate_index")!=i or x.get("archive_index")!=i:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("verified registry index sequence invalid")
        receipt_id=x.get("receipt_id")
        if not isinstance(receipt_id,str) or not receipt_id.startswith("FRC-") or receipt_id in seen:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("verified receipt id invalid or duplicate")
        seen.add(receipt_id)
        q,p=x.get("filled_quantity"),x.get("fill_price")
        if isinstance(q,bool) or not isinstance(q,int) or q<=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("quantity invalid")
        if isinstance(p,bool) or not isinstance(p,(int,float)) or float(p)<=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("price invalid")
        if x.get("notional_value")!=round(float(p)*q,10): raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("notional invalid")
        if x.get("verification_state")!="VERIFIED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("verified registry receipt state invalid")

    if len(s.get("verification_checks",[]))!=12 or len(s.get("verification_ledger",[]))!=6:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("verification checks or ledger invalid")
    gate=s.get("verification_gate",{})
    expected={"archive_certificate_registry_verified":True,"registry_immutable":True,
              "registry_effect":"OFFLINE_INFORMATIONAL_REGISTRATION_ONLY",
              "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
              "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
              "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"verification_gate {k} invalid")
    for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created","external_orders_submitted","broker_routes_created"):
        if s.get(k)!=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"mutation detected: {k}")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","approved_for_live","network_used"):
        if s.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError(f"unsafe source state: {k}")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError("safety lock invalid")
    return index

def build_snapshot(source:Dict[str,Any],config:Dict[str,Any],snapshotted_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config); index=validate_source(source)
    when=datetime.now(timezone.utc).replace(microsecond=0).isoformat() if snapshotted_at is None else parse_ts(snapshotted_at)
    snapshot_id="FRS-"+hashlib.sha256(
        f"{source['fill_receipt_archive_certificate_registry_verification_id']}|"
        f"{source['offline_paper_fill_receipt_archive_certificate_registry_verification_sha256']}|{when}|{VERSION}".encode()
    ).hexdigest()[:16].upper()
    manifest={"snapshot_id":snapshot_id,
      "registry_verification_id":source["fill_receipt_archive_certificate_registry_verification_id"],
      "registry_id":source["fill_receipt_archive_certificate_registry_id"],
      "certificate_id":source["fill_receipt_archive_certificate_id"],
      "receipt_batch_id":source["receipt_batch_id"],"snapshotted_receipt_count":len(index),
      "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY",
      "snapshot_state":"SEALED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "snapshotted_at":when}
    snap_index=[{"snapshot_index":i,"registry_index":x["registry_index"],"certificate_index":x["certificate_index"],
      "archive_index":x["archive_index"],"receipt_id":x["receipt_id"],"receipt_sha256":x["receipt_sha256"],
      "fill_id":x["fill_id"],"symbol":x["symbol"],"side":x["side"],"filled_quantity":x["filled_quantity"],
      "fill_price":x["fill_price"],"notional_value":x["notional_value"],
      "snapshot_state":"SNAPSHOTTED_VERIFIED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"} for i,x in enumerate(index,1)]
    checks=[{"check_index":i,"check":n,"state":st} for i,(n,st) in enumerate([
      ("REGISTRY_VERIFICATION_INTEGRITY","PASS"),("VERIFIED_REGISTRY_INDEX_INTEGRITY","PASS"),
      ("VERIFICATION_CHECKS_INTEGRITY","PASS"),("VERIFICATION_LEDGER_INTEGRITY","PASS"),
      ("SNAPSHOT_ID_DETERMINISTIC","PASS"),("SNAPSHOT_MANIFEST_CREATED","PASS"),
      ("SNAPSHOT_INDEX_CREATED","PASS"),("RECEIPT_LINKAGES_AND_NOTIONALS_PRESERVED","PASS"),
      ("SNAPSHOT_CONTENT_IMMUTABLE","LOCKED"),("SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT","ENFORCED"),
      ("NETWORK_AND_BROKER_DISABLED","PASS"),("LIVE_TRADING_PROHIBITION","ENFORCED")],1)]
    ledger=[{"ledger_index":i,"event":e,"state":st,"snapshot_id":snapshot_id} for i,(e,st) in enumerate([
      ("REGISTRY_VERIFICATION_ACCEPTED","PASS"),("SNAPSHOT_MANIFEST_CREATED","CREATED"),
      ("VERIFIED_REGISTRY_INDEX_SNAPSHOTTED","SNAPSHOTTED"),("SNAPSHOT_CONTENT_SEALED","LOCKED"),
      ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT","ENFORCED"),
      ("OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_COMPLETED","SEALED")],1)]
    out={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_created",
      "fill_receipt_archive_certificate_registry_snapshot_id":snapshot_id,
      "fill_receipt_archive_certificate_registry_verification_id":source["fill_receipt_archive_certificate_registry_verification_id"],
      "fill_receipt_archive_certificate_registry_id":source["fill_receipt_archive_certificate_registry_id"],
      "fill_receipt_archive_certificate_verification_id":source["fill_receipt_archive_certificate_verification_id"],
      "fill_receipt_archive_certificate_id":source["fill_receipt_archive_certificate_id"],
      "fill_receipt_archive_verification_id":source["fill_receipt_archive_verification_id"],
      "fill_receipt_archive_package_id":source["fill_receipt_archive_package_id"],
      "fill_receipt_verification_id":source["fill_receipt_verification_id"],"receipt_batch_id":source["receipt_batch_id"],
      "snapshot_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
      "snapshot_state":"SEALED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "snapshotted_at":when,"snapshot_manifest":manifest,"snapshot_manifest_sha256":sha256_of(manifest),
      "snapshotted_receipt_count":len(snap_index),"snapshot_index":snap_index,"snapshot_index_sha256":sha256_of(snap_index),
      "snapshot_checks":checks,"snapshot_checks_sha256":sha256_of(checks),
      "snapshot_ledger":ledger,"snapshot_ledger_sha256":sha256_of(ledger),
      "snapshot_gate":{"archive_certificate_registry_snapshot_created":True,"snapshot_immutable":True,
        "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY","settlement_execution_allowed":False,
        "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
        "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
        "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2AL"},
      "source_registry_verification_sha256":source["offline_paper_fill_receipt_archive_certificate_registry_verification_sha256"],
      "source_verified_registry_index_sha256":source["verified_registry_index_sha256"],
      "source_verification_checks_sha256":source["verification_checks_sha256"],
      "source_verification_ledger_sha256":source["verification_ledger_sha256"],
      "session_id":source["session_id"],"cycle_id":source["cycle_id"],"cycle_sequence":source["cycle_sequence"],
      "champion_candidate_id":source["champion_candidate_id"],"settlements_created":0,"positions_updated":0,
      "cash_updates_created":0,"portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
      "approved_for_live":False,"network_used":False,"safety_lock":copy.deepcopy(source["safety_lock"]),
      "schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256"]=sha256_of(out)
    return out

def write_outputs(o:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_v75_2ak.json":o,
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_manifest_v75_2ak.json":{
        "snapshot_id":o["fill_receipt_archive_certificate_registry_snapshot_id"],
        "snapshot_manifest":o["snapshot_manifest"],"snapshot_manifest_sha256":o["snapshot_manifest_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_index_v75_2ak.json":{
        "snapshot_id":o["fill_receipt_archive_certificate_registry_snapshot_id"],
        "snapshotted_receipt_count":o["snapshotted_receipt_count"],"snapshot_index":o["snapshot_index"],
        "snapshot_index_sha256":o["snapshot_index_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_ledger_v75_2ak.json":{
        "snapshot_id":o["fill_receipt_archive_certificate_registry_snapshot_id"],
        "snapshot_ledger":o["snapshot_ledger"],"snapshot_ledger_sha256":o["snapshot_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_fill_receipt_archive_certificate_registry_snapshot_v75_2ak.sha256").write_text(
      o["offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--snapshotted-at")
    a=p.parse_args(argv)
    try:
        o=build_snapshot(read_json(Path(a.input)),read_json(Path(a.config)),a.snapshotted_at); write_outputs(o,Path(a.output_dir))
        print(json.dumps({k:o[k] for k in ("status","decision","fill_receipt_archive_certificate_registry_snapshot_id",
          "snapshot_state","snapshotted_receipt_count","settlements_created","positions_updated","cash_updates_created",
          "portfolio_updates_created","external_orders_submitted","broker_routes_created","network_used","approved_for_live",
          "offline_paper_fill_receipt_archive_certificate_registry_snapshot_sha256")},indent=2,sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_failed",
          "error":str(e),"settlements_created":0,"positions_updated":0,"cash_updates_created":0,
          "portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
          "network_used":False,"approved_for_live":False,"version":VERSION},indent=2,sort_keys=True))
        return 1
if __name__=="__main__": raise SystemExit(main())
