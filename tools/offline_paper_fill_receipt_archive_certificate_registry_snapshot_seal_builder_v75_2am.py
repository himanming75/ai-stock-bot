from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2AM"
SCHEMA="v75.2am.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal.1"
SOURCE_SCHEMA="v75.2al.offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification.1"
SOURCE_VERSION="75.2AL"

class OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("top-level JSON must be an object")
    return v

def parse_ts(v:str)->str:
    if not isinstance(v,str) or not v: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("sealed_at invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("sealed_at must be ISO-8601") from e
    if d.tzinfo is None: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("sealed_at must include timezone")
    return d.isoformat()

def validate_config(c:Dict[str,Any])->None:
    if c.get("seal_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("seal_scope invalid")
    for k in ("require_snapshot_verification_integrity","require_verified_snapshot_index_integrity",
              "require_verification_checks_integrity","require_verification_ledger_integrity",
              "require_zero_settlement_and_account_mutations","create_seal_manifest",
              "create_sealed_index","create_seal_checks","create_seal_ledger"):
        if c.get(k) is not True: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"{k} must be true")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS": raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA or s.get("version")!=SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("unsupported source schema or version")
    if s.get("decision")!="offline_paper_fill_receipt_archive_certificate_registry_snapshot_verified":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("source decision invalid")
    if s.get("verification_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("source verification scope invalid")
    if s.get("verification_state")!="VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT" or s.get("archive_certificate_registry_snapshot_verified") is not True:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("snapshot verification incomplete")

    observed=s.get("offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256")
    clone=copy.deepcopy(s); clone.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256",None)
    if observed!=sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("snapshot verification integrity failed")
    for f,h in (("verified_snapshot_index","verified_snapshot_index_sha256"),
                ("verification_checks","verification_checks_sha256"),("verification_ledger","verification_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(f)):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"{f} integrity failed")

    svid=s.get("fill_receipt_archive_certificate_registry_snapshot_verification_id")
    sid=s.get("fill_receipt_archive_certificate_registry_snapshot_id")
    if not isinstance(svid,str) or not svid.startswith("FSV-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("snapshot verification id invalid")
    if not isinstance(sid,str) or not sid.startswith("FRS-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("snapshot id invalid")

    index=s.get("verified_snapshot_index")
    if not isinstance(index,list) or not index:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("verified snapshot index required")
    if s.get("verified_snapshotted_receipt_count")!=len(index):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("verified snapshot receipt count mismatch")
    seen=set()
    for i,x in enumerate(index,1):
        if not isinstance(x,dict) or x.get("snapshot_index")!=i or x.get("registry_index")!=i or x.get("certificate_index")!=i or x.get("archive_index")!=i:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("verified snapshot index sequence invalid")
        rid=x.get("receipt_id")
        if not isinstance(rid,str) or not rid.startswith("FRC-") or rid in seen:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("verified snapshot receipt id invalid or duplicate")
        seen.add(rid)
        q,p=x.get("filled_quantity"),x.get("fill_price")
        if isinstance(q,bool) or not isinstance(q,int) or q<=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("quantity invalid")
        if isinstance(p,bool) or not isinstance(p,(int,float)) or float(p)<=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("price invalid")
        if x.get("notional_value")!=round(float(p)*q,10): raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("notional invalid")
        if x.get("verification_state")!="VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("verified snapshot receipt state invalid")

    if len(s.get("verification_checks",[]))!=12 or len(s.get("verification_ledger",[]))!=6:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("verification checks or ledger invalid")
    gate=s.get("verification_gate",{})
    expected={"archive_certificate_registry_snapshot_verified":True,"snapshot_immutable":True,
      "snapshot_effect":"OFFLINE_IMMUTABLE_EVIDENCE_ONLY","settlement_execution_allowed":False,
      "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
      "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"verification_gate {k} invalid")
    for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created","external_orders_submitted","broker_routes_created"):
        if s.get(k)!=0: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"mutation detected: {k}")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","approved_for_live","network_used"):
        if s.get(k) is not False: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError(f"unsafe source state: {k}")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError("safety lock invalid")
    return index

def build_seal(source:Dict[str,Any],config:Dict[str,Any],sealed_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config); index=validate_source(source)
    when=datetime.now(timezone.utc).replace(microsecond=0).isoformat() if sealed_at is None else parse_ts(sealed_at)
    seal_id="FSS-"+hashlib.sha256(
      f"{source['fill_receipt_archive_certificate_registry_snapshot_verification_id']}|"
      f"{source['offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256']}|{when}|{VERSION}".encode()
    ).hexdigest()[:16].upper()
    manifest={"seal_id":seal_id,
      "snapshot_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_verification_id"],
      "snapshot_id":source["fill_receipt_archive_certificate_registry_snapshot_id"],
      "registry_id":source["fill_receipt_archive_certificate_registry_id"],
      "certificate_id":source["fill_receipt_archive_certificate_id"],
      "receipt_batch_id":source["receipt_batch_id"],"sealed_receipt_count":len(index),
      "seal_effect":"OFFLINE_FINAL_IMMUTABLE_EVIDENCE_SEAL_ONLY",
      "seal_state":"SEALED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "sealed_at":when}
    sealed_index=[{"seal_index":i,"snapshot_index":x["snapshot_index"],"registry_index":x["registry_index"],
      "certificate_index":x["certificate_index"],"archive_index":x["archive_index"],
      "receipt_id":x["receipt_id"],"receipt_sha256":x["receipt_sha256"],"fill_id":x["fill_id"],
      "symbol":x["symbol"],"side":x["side"],"filled_quantity":x["filled_quantity"],
      "fill_price":x["fill_price"],"notional_value":x["notional_value"],
      "seal_state":"SEALED_VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"} for i,x in enumerate(index,1)]
    checks=[{"check_index":i,"check":n,"state":st} for i,(n,st) in enumerate([
      ("SNAPSHOT_VERIFICATION_INTEGRITY","PASS"),("VERIFIED_SNAPSHOT_INDEX_INTEGRITY","PASS"),
      ("VERIFICATION_CHECKS_INTEGRITY","PASS"),("VERIFICATION_LEDGER_INTEGRITY","PASS"),
      ("SEAL_ID_DETERMINISTIC","PASS"),("SEAL_MANIFEST_CREATED","PASS"),
      ("SEALED_INDEX_CREATED","PASS"),("RECEIPT_LINKAGES_AND_NOTIONALS_PRESERVED","PASS"),
      ("SEAL_CONTENT_IMMUTABLE","LOCKED"),("SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT","ENFORCED"),
      ("NETWORK_AND_BROKER_DISABLED","PASS"),("LIVE_TRADING_PROHIBITION","ENFORCED")],1)]
    ledger=[{"ledger_index":i,"event":e,"state":st,"seal_id":seal_id} for i,(e,st) in enumerate([
      ("SNAPSHOT_VERIFICATION_ACCEPTED","PASS"),("SEAL_MANIFEST_CREATED","CREATED"),
      ("VERIFIED_SNAPSHOT_INDEX_SEALED","SEALED"),("SEAL_CONTENT_LOCKED","LOCKED"),
      ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT","ENFORCED"),
      ("OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_COMPLETED","SEALED")],1)]
    out={"status":"PASS","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_sealed",
      "fill_receipt_archive_certificate_registry_snapshot_seal_id":seal_id,
      "fill_receipt_archive_certificate_registry_snapshot_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_verification_id"],
      "fill_receipt_archive_certificate_registry_snapshot_id":source["fill_receipt_archive_certificate_registry_snapshot_id"],
      "fill_receipt_archive_certificate_registry_verification_id":source["fill_receipt_archive_certificate_registry_verification_id"],
      "fill_receipt_archive_certificate_registry_id":source["fill_receipt_archive_certificate_registry_id"],
      "fill_receipt_archive_certificate_verification_id":source["fill_receipt_archive_certificate_verification_id"],
      "fill_receipt_archive_certificate_id":source["fill_receipt_archive_certificate_id"],
      "fill_receipt_archive_verification_id":source["fill_receipt_archive_verification_id"],
      "fill_receipt_archive_package_id":source["fill_receipt_archive_package_id"],
      "fill_receipt_verification_id":source["fill_receipt_verification_id"],"receipt_batch_id":source["receipt_batch_id"],
      "seal_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY",
      "seal_state":"SEALED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT",
      "sealed_at":when,"seal_manifest":manifest,"seal_manifest_sha256":sha256_of(manifest),
      "sealed_receipt_count":len(sealed_index),"sealed_index":sealed_index,"sealed_index_sha256":sha256_of(sealed_index),
      "seal_checks":checks,"seal_checks_sha256":sha256_of(checks),
      "seal_ledger":ledger,"seal_ledger_sha256":sha256_of(ledger),
      "seal_gate":{"archive_certificate_registry_snapshot_sealed":True,"seal_immutable":True,
        "seal_effect":"OFFLINE_FINAL_IMMUTABLE_EVIDENCE_SEAL_ONLY","settlement_execution_allowed":False,
        "position_update_allowed":False,"cash_update_allowed":False,"portfolio_update_allowed":False,
        "external_order_submission_allowed":False,"broker_routing_allowed":False,"paper_broker_allowed":False,
        "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2AN"},
      "source_snapshot_verification_sha256":source["offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_sha256"],
      "source_verified_snapshot_index_sha256":source["verified_snapshot_index_sha256"],
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
    out["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_sha256"]=sha256_of(out)
    return out

def write_outputs(o:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_v75_2am.json":o,
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_manifest_v75_2am.json":{
        "seal_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_id"],
        "seal_manifest":o["seal_manifest"],"seal_manifest_sha256":o["seal_manifest_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_sealed_index_v75_2am.json":{
        "seal_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_id"],
        "sealed_receipt_count":o["sealed_receipt_count"],"sealed_index":o["sealed_index"],
        "sealed_index_sha256":o["sealed_index_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_ledger_v75_2am.json":{
        "seal_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_id"],
        "seal_ledger":o["seal_ledger"],"seal_ledger_sha256":o["seal_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_v75_2am.sha256").write_text(
      o["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--sealed-at")
    a=p.parse_args(argv)
    try:
        o=build_seal(read_json(Path(a.input)),read_json(Path(a.config)),a.sealed_at); write_outputs(o,Path(a.output_dir))
        print(json.dumps({k:o[k] for k in ("status","decision","fill_receipt_archive_certificate_registry_snapshot_seal_id",
          "seal_state","sealed_receipt_count","settlements_created","positions_updated","cash_updates_created",
          "portfolio_updates_created","external_orders_submitted","broker_routes_created","network_used","approved_for_live",
          "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_sha256")},indent=2,sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL","decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_failed",
          "error":str(e),"settlements_created":0,"positions_updated":0,"cash_updates_created":0,
          "portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
          "network_used":False,"approved_for_live":False,"version":VERSION},indent=2,sort_keys=True))
        return 1
if __name__=="__main__": raise SystemExit(main())
