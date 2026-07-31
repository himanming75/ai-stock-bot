from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AT"
SCHEMA = "v75.2at.offline_paper_certificate_registry_snapshot_verification.1"
SOURCE_VERSION = "75.2AS"
SOURCE_SCHEMA = "v75.2as.offline_paper_certificate_registry_snapshot.1"


class RegistrySnapshotVerificationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistrySnapshotVerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistrySnapshotVerificationError(f"invalid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise RegistrySnapshotVerificationError("top-level JSON must be an object")
    return data


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("verification_scope") != "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY":
        raise RegistrySnapshotVerificationError("verification_scope invalid")

    required_true = (
        "require_snapshot_integrity",
        "require_snapshot_manifest_integrity",
        "require_snapshot_index_integrity",
        "require_snapshot_checks_integrity",
        "require_snapshot_ledger_integrity",
        "require_deterministic_snapshot_id",
        "require_receipt_linkage_and_notional_preservation",
        "require_zero_settlement_and_account_mutations",
        "create_verified_snapshot_index",
        "create_verification_checks",
        "create_verification_ledger",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise RegistrySnapshotVerificationError(f"{key} must be true")

    required_false = (
        "settlement_execution_allowed",
        "position_update_allowed",
        "cash_update_allowed",
        "portfolio_update_allowed",
        "external_order_submission_allowed",
        "broker_routing_allowed",
        "paper_broker_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    )
    for key in required_false:
        if config.get(key) is not False:
            raise RegistrySnapshotVerificationError(f"{key} must be false")


def expected_snapshot_id(source: Dict[str, Any]) -> str:
    seed = (
        f"{source['certificate_registry_verification_id']}|"
        f"{source['source_registry_verification_sha256']}|"
        f"{source['snapshotted_at']}|{SOURCE_VERSION}"
    )
    return "CRSN-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper()


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise RegistrySnapshotVerificationError("source status must be PASS")
    if source.get("version") != SOURCE_VERSION or source.get("schema_version") != SOURCE_SCHEMA:
        raise RegistrySnapshotVerificationError("unsupported source version or schema")
    if source.get("decision") != "offline_paper_certificate_registry_snapshot_created":
        raise RegistrySnapshotVerificationError("source decision invalid")
    if source.get("snapshot_scope") != "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY":
        raise RegistrySnapshotVerificationError("snapshot scope invalid")
    if source.get("snapshot_state") != "SNAPSHOTTED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY":
        raise RegistrySnapshotVerificationError("snapshot state invalid")

    observed = source.get("offline_paper_certificate_registry_snapshot_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_certificate_registry_snapshot_sha256", None)
    if observed != sha256_of(clone):
        raise RegistrySnapshotVerificationError("snapshot integrity failed")

    for field, hash_field in (
        ("snapshot_manifest", "snapshot_manifest_sha256"),
        ("snapshot_index", "snapshot_index_sha256"),
        ("snapshot_checks", "snapshot_checks_sha256"),
        ("snapshot_ledger", "snapshot_ledger_sha256"),
    ):
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise RegistrySnapshotVerificationError(f"{field} integrity failed")

    snapshot_id = source.get("certificate_registry_snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("CRSN-"):
        raise RegistrySnapshotVerificationError("snapshot id invalid")
    if snapshot_id != expected_snapshot_id(source):
        raise RegistrySnapshotVerificationError("snapshot id is not deterministic")

    verification_id = source.get("certificate_registry_verification_id")
    registry_id = source.get("certificate_registry_id")
    if not isinstance(verification_id, str) or not verification_id.startswith("FCRX-"):
        raise RegistrySnapshotVerificationError("registry verification id invalid")
    if not isinstance(registry_id, str) or not registry_id.startswith("FCRS-"):
        raise RegistrySnapshotVerificationError("registry id invalid")

    manifest = source.get("snapshot_manifest")
    if not isinstance(manifest, dict):
        raise RegistrySnapshotVerificationError("snapshot manifest required")

    expected_manifest = {
        "snapshot_id": snapshot_id,
        "registry_verification_id": verification_id,
        "registry_id": registry_id,
        "receipt_batch_id": source.get("receipt_batch_id"),
        "snapshot_receipt_count": source.get("snapshot_receipt_count"),
        "snapshot_effect": "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
        "snapshot_state": "SNAPSHOTTED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY",
        "snapshotted_at": source.get("snapshotted_at"),
    }
    if manifest != expected_manifest:
        raise RegistrySnapshotVerificationError("snapshot manifest content invalid")

    index = source.get("snapshot_index")
    if not isinstance(index, list) or not index:
        raise RegistrySnapshotVerificationError("snapshot index required")
    if source.get("snapshot_receipt_count") != len(index):
        raise RegistrySnapshotVerificationError("snapshot receipt count mismatch")

    seen_receipts = set()
    for i, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise RegistrySnapshotVerificationError("snapshot index item invalid")
        if item.get("snapshot_record_index") != i:
            raise RegistrySnapshotVerificationError("snapshot index sequence invalid")

        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-"):
            raise RegistrySnapshotVerificationError("receipt id invalid")
        if receipt_id in seen_receipts:
            raise RegistrySnapshotVerificationError("duplicate receipt id")
        seen_receipts.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise RegistrySnapshotVerificationError("filled quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise RegistrySnapshotVerificationError("fill price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise RegistrySnapshotVerificationError("notional value invalid")

        if item.get("snapshot_state") != "SNAPSHOTTED_VERIFIED_REGISTERED_CERTIFIED_SEALED_ARCHIVED_OFFLINE_RECEIPT":
            raise RegistrySnapshotVerificationError("snapshot receipt state invalid")

    if len(source.get("snapshot_checks", [])) != 12:
        raise RegistrySnapshotVerificationError("snapshot checks invalid")
    if len(source.get("snapshot_ledger", [])) != 6:
        raise RegistrySnapshotVerificationError("snapshot ledger invalid")

    gate = source.get("snapshot_gate", {})
    expected_gate = {
        "certificate_registry_snapshot_created": True,
        "snapshot_immutable": True,
        "snapshot_effect": "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_ONLY",
        "settlement_execution_allowed": False,
        "position_update_allowed": False,
        "cash_update_allowed": False,
        "portfolio_update_allowed": False,
        "external_order_submission_allowed": False,
        "broker_routing_allowed": False,
        "paper_broker_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    for key, value in expected_gate.items():
        if gate.get(key) != value:
            raise RegistrySnapshotVerificationError(f"snapshot_gate {key} invalid")

    for key in (
        "settlements_created",
        "positions_updated",
        "cash_updates_created",
        "portfolio_updates_created",
        "external_orders_submitted",
        "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise RegistrySnapshotVerificationError(f"mutation detected: {key}")

    for key in (
        "settlement_execution_allowed",
        "position_update_allowed",
        "cash_update_allowed",
        "portfolio_update_allowed",
        "external_order_submission_allowed",
        "broker_routing_allowed",
        "paper_broker_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "approved_for_live",
        "network_used",
    ):
        if source.get(key) is not False:
            raise RegistrySnapshotVerificationError(f"unsafe source state: {key}")

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise RegistrySnapshotVerificationError("safety lock invalid")

    return index


def verify_snapshot(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    verification_seed = (
        f"{source['certificate_registry_snapshot_id']}|"
        f"{source['offline_paper_certificate_registry_snapshot_sha256']}|"
        f"{VERSION}"
    )
    verification_id = "CRSX-" + hashlib.sha256(
        verification_seed.encode("utf-8")
    ).hexdigest()[:16].upper()

    verified_index = [
        {
            "verification_record_index": i,
            "snapshot_record_index": item["snapshot_record_index"],
            "registry_record_index": item["registry_record_index"],
            "receipt_id": item["receipt_id"],
            "receipt_sha256": item["receipt_sha256"],
            "fill_id": item["fill_id"],
            "symbol": item["symbol"],
            "side": item["side"],
            "filled_quantity": item["filled_quantity"],
            "fill_price": item["fill_price"],
            "notional_value": item["notional_value"],
            "verification_state": "VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_SEALED_ARCHIVED_OFFLINE_RECEIPT",
        }
        for i, item in enumerate(index, 1)
    ]

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate(
            (
                ("SNAPSHOT_INTEGRITY", "PASS"),
                ("SNAPSHOT_MANIFEST_INTEGRITY", "PASS"),
                ("SNAPSHOT_INDEX_INTEGRITY", "PASS"),
                ("SNAPSHOT_CHECKS_INTEGRITY", "PASS"),
                ("SNAPSHOT_LEDGER_INTEGRITY", "PASS"),
                ("DETERMINISTIC_SNAPSHOT_ID", "PASS"),
                ("RECEIPT_LINKAGE_PRESERVED", "PASS"),
                ("NOTIONAL_VALUES_PRESERVED", "PASS"),
                ("SNAPSHOT_IMMUTABILITY", "LOCKED"),
                ("SETTLEMENT_ACCOUNT_MUTATIONS_ABSENT", "ENFORCED"),
                ("NETWORK_AND_BROKER_DISABLED", "PASS"),
                ("LIVE_TRADING_PROHIBITION", "ENFORCED"),
            ),
            1,
        )
    ]

    ledger = [
        {
            "ledger_index": i,
            "event": event,
            "state": state,
            "snapshot_verification_id": verification_id,
        }
        for i, (event, state) in enumerate(
            (
                ("CERTIFICATE_REGISTRY_SNAPSHOT_ACCEPTED", "PASS"),
                ("SNAPSHOT_MANIFEST_VERIFIED", "VERIFIED"),
                ("SNAPSHOT_INDEX_VERIFIED", "VERIFIED"),
                ("SNAPSHOT_EVIDENCE_LOCK_CONFIRMED", "LOCKED"),
                ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT", "ENFORCED"),
                ("OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_COMPLETED", "VERIFIED"),
            ),
            1,
        )
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_certificate_registry_snapshot_verified",
        "certificate_registry_snapshot_verification_id": verification_id,
        "certificate_registry_snapshot_id": source["certificate_registry_snapshot_id"],
        "certificate_registry_verification_id": source["certificate_registry_verification_id"],
        "certificate_registry_id": source["certificate_registry_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "verification_scope": "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY",
        "verification_state": "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT",
        "snapshot_verified": True,
        "verified_snapshot_receipt_count": len(verified_index),
        "verified_snapshot_index": verified_index,
        "verified_snapshot_index_sha256": sha256_of(verified_index),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "certificate_registry_snapshot_verified": True,
            "snapshot_immutable": True,
            "verification_effect": "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY",
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AU",
        },
        "source_snapshot_sha256": source["offline_paper_certificate_registry_snapshot_sha256"],
        "source_snapshot_manifest_sha256": source["snapshot_manifest_sha256"],
        "source_snapshot_index_sha256": source["snapshot_index_sha256"],
        "source_snapshot_checks_sha256": source["snapshot_checks_sha256"],
        "source_snapshot_ledger_sha256": source["snapshot_ledger_sha256"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "settlements_created": 0,
        "positions_updated": 0,
        "cash_updates_created": 0,
        "portfolio_updates_created": 0,
        "external_orders_submitted": 0,
        "broker_routes_created": 0,
        "settlement_execution_allowed": False,
        "position_update_allowed": False,
        "cash_update_allowed": False,
        "portfolio_update_allowed": False,
        "external_order_submission_allowed": False,
        "broker_routing_allowed": False,
        "paper_broker_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(source["safety_lock"]),
        "schema_version": SCHEMA,
        "version": VERSION,
    }

    output["offline_paper_certificate_registry_snapshot_verification_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_verification_v75_2at.json": output,
        "verified_snapshot_index_v75_2at.json": {
            "snapshot_verification_id": output["certificate_registry_snapshot_verification_id"],
            "verified_snapshot_receipt_count": output["verified_snapshot_receipt_count"],
            "verified_snapshot_index": output["verified_snapshot_index"],
            "verified_snapshot_index_sha256": output["verified_snapshot_index_sha256"],
        },
        "registry_snapshot_verification_checks_v75_2at.json": {
            "snapshot_verification_id": output["certificate_registry_snapshot_verification_id"],
            "verification_checks": output["verification_checks"],
            "verification_checks_sha256": output["verification_checks_sha256"],
        },
        "registry_snapshot_verification_ledger_v75_2at.json": {
            "snapshot_verification_id": output["certificate_registry_snapshot_verification_id"],
            "verification_ledger": output["verification_ledger"],
            "verification_ledger_sha256": output["verification_ledger_sha256"],
        },
    }

    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (output_dir / "registry_snapshot_verification_v75_2at.sha256").write_text(
        output["offline_paper_certificate_registry_snapshot_verification_sha256"] + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        output = verify_snapshot(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
        )
        write_outputs(output, Path(args.output_dir))

        keys = (
            "status",
            "decision",
            "certificate_registry_snapshot_verification_id",
            "verification_state",
            "verified_snapshot_receipt_count",
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
            "network_used",
            "approved_for_live",
            "offline_paper_certificate_registry_snapshot_verification_sha256",
        )
        print(json.dumps({key: output[key] for key in keys}, indent=2, sort_keys=True))
        return 0

    except (
        RegistrySnapshotVerificationError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "decision": "offline_paper_certificate_registry_snapshot_verification_failed",
                    "error": str(exc),
                    "settlements_created": 0,
                    "positions_updated": 0,
                    "cash_updates_created": 0,
                    "portfolio_updates_created": 0,
                    "external_orders_submitted": 0,
                    "broker_routes_created": 0,
                    "network_used": False,
                    "approved_for_live": False,
                    "version": VERSION,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
