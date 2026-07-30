from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION="75.2AS"
SCHEMA="v75.2as.offline_paper_certificate_registry_snapshot.1"
SOURCE_SCHEMA="v75.2ar.offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification.1"
SOURCE_VERSION="75.2AR"

class RegistrySnapshotError(ValueError): pass

def canonical_json(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_of(v:Any)->str:
    return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def read_json(path:Path)->Dict[str,Any]:
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise RegistrySnapshotError(f"file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise RegistrySnapshotError(f"invalid JSON: {path}") from e
    if not isinstance(data,dict):
        raise RegistrySnapshotError("top-level JSON must be an object")
    return data

def parse_timestamp(value:str)->str:
    if not isinstance(value,str) or not value:
        raise RegistrySnapshotError("snapshotted_at invalid")
    try:
        dt=datetime.fromisoformat(value)
    except ValueError as e:
        raise RegistrySnapshotError("snapshotted_at must be ISO-8601") from e
    if dt.tzinfo is None:
        raise RegistrySnapshotError("snapshotted_at must include timezone")
    return dt.isoformat()

def validate_config(config:Dict[str,Any])->None:
    if config.get("snapshot_scope")!="OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY":
        raise RegistrySnapshotError("snapshot_scope invalid")
    for key in (
        "require_registry_verification_integrity",
        "require_verified_registered_index_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_zero_settlement_and_account_mutations",
        "create_snapshot_manifest",
        "create_snapshot_index",
        "create_snapshot_checks",
        "create_snapshot_ledger",
    ):
        if config.get(key) is not True:
            raise RegistrySnapshotError(f"{key} must be true")
    for key in (
        "settlement_execution_allowed","position_update_allowed","cash_update_allowed",
        "portfolio_update_allowed","external_order_submission_allowed","broker_routing_allowed",
        "paper_broker_allowed","live_orders_allowed","network_allowed",
        "broker_connection_allowed","external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise RegistrySnapshotError(f"{key} must be false")

def validate_source(source:Dict[str,Any])->List[Dict[str,Any]]:
    if source.get("status")!="PASS":
        raise RegistrySnapshotError("source status must be PASS")
    if source.get("schema_version")!=SOURCE_SCHEMA or source.get("version")!=SOURCE_VERSION:
        raise RegistrySnapshotError("unsupported source schema or version")
    if source.get("decision")!="offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verified":
        raise RegistrySnapshotError("source decision invalid")
    if source.get("verification_scope")!="OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY_VERIFICATION_ONLY":
        raise RegistrySnapshotError("source verification scope invalid")
    if source.get("verification_state")!="VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_REGISTRY":
        raise RegistrySnapshotError("source verification state invalid")
    if source.get("archive_certificate_registry_snapshot_seal_certificate_registry_verified") is not True:
        raise RegistrySnapshotError("registry verification incomplete")

    observed=source.get("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256")
    clone=copy.deepcopy(source)
    clone.pop("offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256",None)
    if observed!=sha256_of(clone):
        raise RegistrySnapshotError("registry verification integrity failed")

    for field,hash_field in (
        ("verified_registered_index","verified_registered_index_sha256"),
        ("verification_checks","verification_checks_sha256"),
        ("verification_ledger","verification_ledger_sha256"),
    ):
        if source.get(hash_field)!=sha256_of(source.get(field)):
            raise RegistrySnapshotError(f"{field} integrity failed")

    verification_id=source.get("fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id")
    registry_id=source.get("fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id")
    if not isinstance(verification_id,str) or not verification_id.startswith("FCRX-"):
        raise RegistrySnapshotError("registry verification id invalid")
    if not isinstance(registry_id,str) or not registry_id.startswith("FCRS-"):
        raise RegistrySnapshotError("registry id invalid")

    index=source.get("verified_registered_index")
    if not isinstance(index,list) or not index:
        raise RegistrySnapshotError("verified registered index required")
    if source.get("verified_registered_receipt_count")!=len(index):
        raise RegistrySnapshotError("verified registered receipt count mismatch")

    seen=set()
    for i,item in enumerate(index,1):
        if not isinstance(item,dict) or item.get("registry_record_index")!=i:
            raise RegistrySnapshotError("verified registered index sequence invalid")
        receipt_id=item.get("receipt_id")
        if not isinstance(receipt_id,str) or not receipt_id.startswith("FRC-") or receipt_id in seen:
            raise RegistrySnapshotError("receipt id invalid or duplicate")
        seen.add(receipt_id)
        quantity=item.get("filled_quantity")
        price=item.get("fill_price")
        if isinstance(quantity,bool) or not isinstance(quantity,int) or quantity<=0:
            raise RegistrySnapshotError("quantity invalid")
        if isinstance(price,bool) or not isinstance(price,(int,float)) or float(price)<=0:
            raise RegistrySnapshotError("price invalid")
        if item.get("notional_value")!=round(float(price)*quantity,10):
            raise RegistrySnapshotError("notional invalid")
        if item.get("verification_state")!="VERIFIED_REGISTERED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise RegistrySnapshotError("verified registered receipt state invalid")

    if len(source.get("verification_checks",[]))!=12 or len(source.get("verification_ledger",[]))!=6:
        raise RegistrySnapshotError("verification checks or ledger invalid")

    gate=source.get("verification_gate",{})
    expected={
        "archive_certificate_registry_snapshot_seal_certificate_registry_verified":True,
        "registry_immutable":True,
        "registry_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_VERIFICATION_ONLY",
        "settlement_execution_allowed":False,
        "position_update_allowed":False,
        "cash_update_allowed":False,
        "portfolio_update_allowed":False,
        "external_order_submission_allowed":False,
        "broker_routing_allowed":False,
        "paper_broker_allowed":False,
        "live_orders_allowed":False,
        "network_allowed":False,
        "next_version":VERSION,
    }
    for key,value in expected.items():
        if gate.get(key)!=value:
            raise RegistrySnapshotError(f"verification_gate {key} invalid")

    for key in (
        "settlements_created","positions_updated","cash_updates_created",
        "portfolio_updates_created","external_orders_submitted","broker_routes_created",
    ):
        if source.get(key)!=0:
            raise RegistrySnapshotError(f"mutation detected: {key}")

    for key in (
        "settlement_execution_allowed","position_update_allowed","cash_update_allowed",
        "portfolio_update_allowed","external_order_submission_allowed","broker_routing_allowed",
        "paper_broker_allowed","live_orders_allowed","network_allowed","broker_connection_allowed",
        "approved_for_live","network_used",
    ):
        if source.get(key) is not False:
            raise RegistrySnapshotError(f"unsafe source state: {key}")

    if source.get("safety_lock",{}).get("lock_state")!="ENFORCED":
        raise RegistrySnapshotError("safety lock invalid")
    return index

def build_snapshot(source:Dict[str,Any],config:Dict[str,Any],snapshotted_at:Optional[str]=None)->Dict[str,Any]:
    validate_config(config)
    index=validate_source(source)
    when=datetime.now(timezone.utc).replace(microsecond=0).isoformat() if snapshotted_at is None else parse_timestamp(snapshotted_at)

    snapshot_id="CRSN-"+hashlib.sha256(
        f"{source['fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id']}|"
        f"{source['offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256']}|"
        f"{when}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    manifest={
        "snapshot_id":snapshot_id,
        "registry_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id"],
        "registry_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id"],
        "receipt_batch_id":source["receipt_batch_id"],
        "snapshot_receipt_count":len(index),
        "snapshot_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
        "snapshot_state":"SNAPSHOTTED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY",
        "snapshotted_at":when,
    }

    snapshot_index=[{
        "snapshot_record_index":i,
        "registry_record_index":item["registry_record_index"],
        "receipt_id":item["receipt_id"],
        "receipt_sha256":item["receipt_sha256"],
        "fill_id":item["fill_id"],
        "symbol":item["symbol"],
        "side":item["side"],
        "filled_quantity":item["filled_quantity"],
        "fill_price":item["fill_price"],
        "notional_value":item["notional_value"],
        "snapshot_state":"SNAPSHOTTED_VERIFIED_REGISTERED_CERTIFIED_SEALED_ARCHIVED_OFFLINE_RECEIPT",
    } for i,item in enumerate(index,1)]

    checks=[{"check_index":i,"check":name,"state":state} for i,(name,state) in enumerate([
        ("REGISTRY_VERIFICATION_INTEGRITY","PASS"),
        ("VERIFIED_REGISTERED_INDEX_INTEGRITY","PASS"),
        ("VERIFICATION_CHECKS_INTEGRITY","PASS"),
        ("VERIFICATION_LEDGER_INTEGRITY","PASS"),
        ("SNAPSHOT_ID_DETERMINISTIC","PASS"),
        ("SNAPSHOT_MANIFEST_CREATED","PASS"),
        ("SNAPSHOT_INDEX_CREATED","PASS"),
        ("RECEIPT_LINKAGES_AND_NOTIONALS_PRESERVED","PASS"),
        ("SNAPSHOT_CONTENT_IMMUTABLE","LOCKED"),
        ("SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT","ENFORCED"),
        ("NETWORK_AND_BROKER_DISABLED","PASS"),
        ("LIVE_TRADING_PROHIBITION","ENFORCED"),
    ],1)]

    ledger=[{"ledger_index":i,"event":event,"state":state,"snapshot_id":snapshot_id}
        for i,(event,state) in enumerate([
            ("REGISTRY_VERIFICATION_ACCEPTED","PASS"),
            ("SNAPSHOT_MANIFEST_CREATED","CREATED"),
            ("VERIFIED_REGISTERED_INDEX_SNAPSHOTTED","SNAPSHOTTED"),
            ("SNAPSHOT_CONTENT_LOCKED","LOCKED"),
            ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT","ENFORCED"),
            ("OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_COMPLETED","SNAPSHOTTED"),
        ],1)]

    out={
        "status":"PASS",
        "decision":"offline_paper_certificate_registry_snapshot_created",
        "certificate_registry_snapshot_id":snapshot_id,
        "certificate_registry_verification_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_id"],
        "certificate_registry_id":source["fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_id"],
        "receipt_batch_id":source["receipt_batch_id"],
        "snapshot_scope":"OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
        "snapshot_state":"SNAPSHOTTED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY",
        "snapshotted_at":when,
        "snapshot_manifest":manifest,
        "snapshot_manifest_sha256":sha256_of(manifest),
        "snapshot_receipt_count":len(snapshot_index),
        "snapshot_index":snapshot_index,
        "snapshot_index_sha256":sha256_of(snapshot_index),
        "snapshot_checks":checks,
        "snapshot_checks_sha256":sha256_of(checks),
        "snapshot_ledger":ledger,
        "snapshot_ledger_sha256":sha256_of(ledger),
        "snapshot_gate":{
            "certificate_registry_snapshot_created":True,
            "snapshot_immutable":True,
            "snapshot_effect":"OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
            "settlement_execution_allowed":False,
            "position_update_allowed":False,
            "cash_update_allowed":False,
            "portfolio_update_allowed":False,
            "external_order_submission_allowed":False,
            "broker_routing_allowed":False,
            "paper_broker_allowed":False,
            "live_orders_allowed":False,
            "network_allowed":False,
            "next_version":"75.2AT",
        },
        "source_registry_verification_sha256":source["offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_certificate_registry_verification_sha256"],
        "source_verified_registered_index_sha256":source["verified_registered_index_sha256"],
        "source_verification_checks_sha256":source["verification_checks_sha256"],
        "source_verification_ledger_sha256":source["verification_ledger_sha256"],
        "session_id":source["session_id"],
        "cycle_id":source["cycle_id"],
        "cycle_sequence":source["cycle_sequence"],
        "champion_candidate_id":source["champion_candidate_id"],
        "settlements_created":0,
        "positions_updated":0,
        "cash_updates_created":0,
        "portfolio_updates_created":0,
        "external_orders_submitted":0,
        "broker_routes_created":0,
        "settlement_execution_allowed":False,
        "position_update_allowed":False,
        "cash_update_allowed":False,
        "portfolio_update_allowed":False,
        "external_order_submission_allowed":False,
        "broker_routing_allowed":False,
        "paper_broker_allowed":False,
        "live_orders_allowed":False,
        "network_allowed":False,
        "broker_connection_allowed":False,
        "approved_for_live":False,
        "network_used":False,
        "safety_lock":copy.deepcopy(source["safety_lock"]),
        "schema_version":SCHEMA,
        "version":VERSION,
    }
    out["offline_paper_certificate_registry_snapshot_sha256"]=sha256_of(out)
    return out

def write_outputs(output:Dict[str,Any],output_dir:Path)->None:
    output_dir.mkdir(parents=True,exist_ok=True)
    payloads={
        "registry_snapshot_v75_2as.json":output,
        "registry_snapshot_manifest_v75_2as.json":{
            "snapshot_id":output["certificate_registry_snapshot_id"],
            "snapshot_manifest":output["snapshot_manifest"],
            "snapshot_manifest_sha256":output["snapshot_manifest_sha256"],
        },
        "registry_snapshot_index_v75_2as.json":{
            "snapshot_id":output["certificate_registry_snapshot_id"],
            "snapshot_receipt_count":output["snapshot_receipt_count"],
            "snapshot_index":output["snapshot_index"],
            "snapshot_index_sha256":output["snapshot_index_sha256"],
        },
        "registry_snapshot_ledger_v75_2as.json":{
            "snapshot_id":output["certificate_registry_snapshot_id"],
            "snapshot_ledger":output["snapshot_ledger"],
            "snapshot_ledger_sha256":output["snapshot_ledger_sha256"],
        },
    }
    for name,payload in payloads.items():
        (output_dir/name).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (output_dir/"registry_snapshot_v75_2as.sha256").write_text(
        output["offline_paper_certificate_registry_snapshot_sha256"]+"\n",encoding="utf-8"
    )

def main(argv:Optional[List[str]]=None)->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--config",required=True)
    parser.add_argument("--output-dir",required=True)
    parser.add_argument("--snapshotted-at")
    args=parser.parse_args(argv)
    try:
        output=build_snapshot(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.snapshotted_at,
        )
        write_outputs(output,Path(args.output_dir))
        keys=(
            "status","decision","certificate_registry_snapshot_id","snapshot_state",
            "snapshot_receipt_count","settlements_created","positions_updated",
            "cash_updates_created","portfolio_updates_created","external_orders_submitted",
            "broker_routes_created","network_used","approved_for_live",
            "offline_paper_certificate_registry_snapshot_sha256",
        )
        print(json.dumps({k:output[k] for k in keys},indent=2,sort_keys=True))
        return 0
    except (RegistrySnapshotError,OSError,KeyError,TypeError,ValueError) as e:
        print(json.dumps({
            "status":"FAIL",
            "decision":"offline_paper_certificate_registry_snapshot_failed",
            "error":str(e),
            "settlements_created":0,
            "positions_updated":0,
            "cash_updates_created":0,
            "portfolio_updates_created":0,
            "external_orders_submitted":0,
            "broker_routes_created":0,
            "network_used":False,
            "approved_for_live":False,
            "version":VERSION,
        },indent=2,sort_keys=True))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
