from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2AQ"
SCHEMA="v75.2aq.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry.1"
SOURCE_SCHEMA="v75.2ap.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification.1"
SOURCE_VERSION="75.2AP"

class OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try: v=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"file not found: {path}") from e
    except json.JSONDecodeError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"invalid JSON: {path}") from e
    if not isinstance(v,dict): raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("top-level JSON must be an object")
    return v

def parse_ts(v:str)->str:
    if not isinstance(v,str) or not v:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("registered_at invalid")
    try: d=datetime.fromisoformat(v)
    except ValueError as e: raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("registered_at must be ISO-8601") from e
    if d.tzinfo is None:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("registered_at must include timezone")
    return d.isoformat()

def validate_config(c:Dict[str,Any])->None:
    if c.get("registry_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("registry_scope invalid")
    for k in ("require_certificate_verification_integrity","require_verified_certified_index_integrity",
              "require_verification_checks_integrity","require_verification_ledger_integrity",
              "require_zero_settlement_and_account_mutations","create_registry_manifest",
              "create_registered_index","create_registry_checks","create_registry_ledger"):
        if c.get(k) is not True:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"{k} must be true")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","external_side_effects_allowed"):
        if c.get(k) is not False:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"{k} must be false")

def validate_source(s:Dict[str,Any])->List[Dict[str,Any]]:
    if s.get("status")!="PASS":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("source status must be PASS")
    if s.get("schema_version")!=SOURCE_SCHEMA or s.get("version")!=SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("unsupported source schema or version")
    if s.get("decision")!="offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verified":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("source decision invalid")
    if s.get("verification_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("source verification scope invalid")
    if s.get("verification_state")!="VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("source verification state invalid")
    if s.get("archive_certificate_registry_snapshot_seal_certificate_verified") is not True:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("certificate verification incomplete")

    observed=s.get("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_sha256")
    clone=copy.deepcopy(s)
    clone.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_sha256",None)
    if observed!=sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("certificate verification integrity failed")
    for f,h in (("verified_certified_index","verified_certified_index_sha256"),
                ("verification_checks","verification_checks_sha256"),
                ("verification_ledger","verification_ledger_sha256")):
        if s.get(h)!=sha256_of(s.get(f)):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"{f} integrity failed")

    verification_id=s.get("fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id")
    certificate_id=s.get("fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id")
    if not isinstance(verification_id,str) or not verification_id.startswith("FCX-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("certificate verification id invalid")
    if not isinstance(certificate_id,str) or not certificate_id.startswith("FSC-"):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("certificate id invalid")

    index=s.get("verified_certified_index")
    if not isinstance(index,list) or not index:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("verified certified index required")
    if s.get("verified_certified_receipt_count")!=len(index):
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("verified certified receipt count mismatch")
    seen=set()
    for i,x in enumerate(index,1):
        if not isinstance(x,dict) or x.get("certificate_record_index")!=i or x.get("seal_index")!=i or x.get("snapshot_index")!=i or x.get("registry_index")!=i or x.get("certificate_index")!=i or x.get("archive_index")!=i:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("verified certified index sequence invalid")
        rid=x.get("receipt_id")
        if not isinstance(rid,str) or not rid.startswith("FRC-") or rid in seen:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("verified certified receipt id invalid or duplicate")
        seen.add(rid)
        q,p=x.get("filled_quantity"),x.get("fill_price")
        if isinstance(q,bool) or not isinstance(q,int) or q<=0:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("quantity invalid")
        if isinstance(p,bool) or not isinstance(p,(int,float)) or float(p)<=0:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("price invalid")
        if x.get("notional_value")!=round(float(p)*q,10):
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("notional invalid")
        if x.get("verification_state")!="VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("verified certified receipt state invalid")

    if len(s.get("verification_checks",[]))!=12 or len(s.get("verification_ledger",[]))!=6:
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("verification checks or ledger invalid")

    gate=s.get("verification_gate",{})
    expected={"archive_certificate_registry_snapshot_seal_certificate_verified":True,
      "certificate_immutable":True,"certificate_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_ONLY",
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,
      "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"next_version":VERSION}
    for k,v in expected.items():
        if gate.get(k)!=v:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"verification_gate {k} invalid")

    for k in ("settlements_created","positions_updated","cash_updates_created","portfolio_updates_created",
              "external_orders_submitted","broker_routes_created"):
        if s.get(k)!=0:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"mutation detected: {k}")
    for k in ("settlement_execution_allowed","position_update_allowed","cash_update_allowed","portfolio_update_allowed",
              "external_order_submission_allowed","broker_routing_allowed","paper_broker_allowed","live_orders_allowed",
              "network_allowed","broker_connection_allowed","approved_for_live","network_used"):
        if s.get(k) is not False:
            raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError(f"unsafe source state: {k}")
    if s.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError("safety lock invalid")
    return index

def build_registry(source:Dict[str,Any],config:Dict[str,Any],registered_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    index=validate_source(source)
    when=datetime.now(timezone.utc).replace(microsecond=0).isoformat() if registered_at is None else parse_ts(registered_at)
    registry_id="FCRS-"+hashlib.sha256(
      f"{source['fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id']}|"
      f"{source['offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_sha256']}|"
      f"{when}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    manifest={"registry_id":registry_id,
      "certificate_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id"],
      "certificate_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id"],
      "seal_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_id"],
      "snapshot_id":source["fill_receipt_archive_certificate_registry_snapshot_id"],
      "receipt_batch_id":source["receipt_batch_id"],"registered_receipt_count":len(index),
      "registry_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRATION_ONLY",
      "registry_state":"REGISTERED_VERIFIED_OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE",
      "registered_at":when}

    registered_index=[{"registry_record_index":i,"certificate_record_index":x["certificate_record_index"],
      "seal_index":x["seal_index"],"snapshot_index":x["snapshot_index"],"registry_index":x["registry_index"],
      "certificate_index":x["certificate_index"],"archive_index":x["archive_index"],
      "receipt_id":x["receipt_id"],"receipt_sha256":x["receipt_sha256"],"fill_id":x["fill_id"],
      "symbol":x["symbol"],"side":x["side"],"filled_quantity":x["filled_quantity"],
      "fill_price":x["fill_price"],"notional_value":x["notional_value"],
      "registry_state":"REGISTERED_VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT"}
      for i,x in enumerate(index,1)]

    checks=[{"check_index":i,"check":n,"state":st} for i,(n,st) in enumerate([
      ("CERTIFICATE_VERIFICATION_INTEGRITY","PASS"),("VERIFIED_CERTIFIED_INDEX_INTEGRITY","PASS"),
      ("VERIFICATION_CHECKS_INTEGRITY","PASS"),("VERIFICATION_LEDGER_INTEGRITY","PASS"),
      ("REGISTRY_ID_DETERMINISTIC","PASS"),("REGISTRY_MANIFEST_CREATED","PASS"),
      ("REGISTERED_INDEX_CREATED","PASS"),("RECEIPT_LINKAGES_AND_NOTIONALS_PRESERVED","PASS"),
      ("REGISTRY_CONTENT_IMMUTABLE","LOCKED"),("SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT","ENFORCED"),
      ("NETWORK_AND_BROKER_DISABLED","PASS"),("LIVE_TRADING_PROHIBITION","ENFORCED")],1)]

    ledger=[{"ledger_index":i,"event":e,"state":st,"registry_id":registry_id} for i,(e,st) in enumerate([
      ("CERTIFICATE_VERIFICATION_ACCEPTED","PASS"),("REGISTRY_MANIFEST_CREATED","CREATED"),
      ("VERIFIED_CERTIFIED_INDEX_REGISTERED","REGISTERED"),("REGISTRY_CONTENT_LOCKED","LOCKED"),
      ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT","ENFORCED"),
      ("OFFLINE_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_COMPLETED","REGISTERED")],1)]

    out={"status":"PASS",
      "decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registered",
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id":registry_id,
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_id"],
      "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_id"],
      "fill_receipt_archive_certificate_registry_snapshot_seal_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_verification_id"],
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
      "registry_scope":"OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_ONLY",
      "registry_state":"REGISTERED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE",
      "registered_at":when,"registry_manifest":manifest,"registry_manifest_sha256":sha256_of(manifest),
      "registered_receipt_count":len(registered_index),"registered_index":registered_index,
      "registered_index_sha256":sha256_of(registered_index),
      "registry_checks":checks,"registry_checks_sha256":sha256_of(checks),
      "registry_ledger":ledger,"registry_ledger_sha256":sha256_of(ledger),
      "registry_gate":{"archive_certificate_registry_snapshot_seal_certificate_registered":True,
        "registry_immutable":True,"registry_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRATION_ONLY",
        "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
        "portfolio_update_allowed":False,"external_order_submission_allowed":False,
        "broker_routing_allowed":False,"paper_broker_allowed":False,"live_orders_allowed":False,
        "network_allowed":False,"next_version":"75.2AR"},
      "source_certificate_verification_sha256":source["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_verification_sha256"],
      "source_verified_certified_index_sha256":source["verified_certified_index_sha256"],
      "source_verification_checks_sha256":source["verification_checks_sha256"],
      "source_verification_ledger_sha256":source["verification_ledger_sha256"],
      "session_id":source["session_id"],"cycle_id":source["cycle_id"],"cycle_sequence":source["cycle_sequence"],
      "champion_candidate_id":source["champion_candidate_id"],"settlements_created":0,"positions_updated":0,
      "cash_updates_created":0,"portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
      "settlement_execution_allowed":False,"position_update_allowed":False,"cash_update_allowed":False,
      "portfolio_update_allowed":False,"external_order_submission_allowed":False,"broker_routing_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"approved_for_live":False,"network_used":False,
      "safety_lock":copy.deepcopy(source["safety_lock"]),"schema_version":SCHEMA,"version":VERSION}
    out["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256"]=sha256_of(out)
    return out

def write_outputs(o:Dict[str,Any],d:Path)->None:
    d.mkdir(parents=True,exist_ok=True)
    payloads={
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_v75_2aq.json":o,
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_manifest_v75_2aq.json":{
        "registry_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id"],
        "registry_manifest":o["registry_manifest"],"registry_manifest_sha256":o["registry_manifest_sha256"]},
      "offline_paper_registered_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_index_v75_2aq.json":{
        "registry_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id"],
        "registered_receipt_count":o["registered_receipt_count"],"registered_index":o["registered_index"],
        "registered_index_sha256":o["registered_index_sha256"]},
      "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_ledger_v75_2aq.json":{
        "registry_id":o["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id"],
        "registry_ledger":o["registry_ledger"],"registry_ledger_sha256":o["registry_ledger_sha256"]}}
    for n,p in payloads.items():
        (d/n).write_text(json.dumps(p,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (d/"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_v75_2aq.sha256").write_text(
      o["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256"]+"\n",encoding="utf-8")

def main(argv:Optional[List[str]]=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--config",required=True)
    p.add_argument("--output-dir",required=True); p.add_argument("--registered-at")
    a=p.parse_args(argv)
    try:
        o=build_registry(read_json(Path(a.input)),read_json(Path(a.config)),a.registered_at)
        write_outputs(o,Path(a.output_dir))
        print(json.dumps({k:o[k] for k in ("status","decision",
          "fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id",
          "registry_state","registered_receipt_count","settlements_created","positions_updated",
          "cash_updates_created","portfolio_updates_created","external_orders_submitted",
          "broker_routes_created","network_used","approved_for_live",
          "offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_sha256")},indent=2,sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveCertificateRegistrySnapshotSealCertificateRegistryError,
            OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({"status":"FAIL",
          "decision":"offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_failed",
          "error":str(e),"settlements_created":0,"positions_updated":0,"cash_updates_created":0,
          "portfolio_updates_created":0,"external_orders_submitted":0,"broker_routes_created":0,
          "network_used":False,"approved_for_live":False,"version":VERSION},indent=2,sort_keys=True))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
