from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AU"
SCHEMA = "v75.2au.offline_paper_certificate_registry_snapshot_seal.1"
SOURCE_VERSION = "75.2AT"
SOURCE_SCHEMA = "v75.2at.offline_paper_certificate_registry_snapshot_verification.1"


class RegistrySnapshotSealError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistrySnapshotSealError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistrySnapshotSealError(f"invalid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise RegistrySnapshotSealError("top-level JSON must be an object")
    return data


def parse_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise RegistrySnapshotSealError("sealed_at invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RegistrySnapshotSealError("sealed_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise RegistrySnapshotSealError("sealed_at must include timezone")
    return parsed.isoformat()


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("seal_scope") != "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY":
        raise RegistrySnapshotSealError("seal_scope invalid")

    required_true = (
        "require_snapshot_verification_integrity",
        "require_verified_snapshot_index_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_zero_settlement_and_account_mutations",
        "create_seal_manifest",
        "create_sealed_snapshot_index",
        "create_seal_checks",
        "create_seal_ledger",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise RegistrySnapshotSealError(f"{key} must be true")

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
            raise RegistrySnapshotSealError(f"{key} must be false")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise RegistrySnapshotSealError("source status must be PASS")
    if source.get("version") != SOURCE_VERSION or source.get("schema_version") != SOURCE_SCHEMA:
        raise RegistrySnapshotSealError("unsupported source version or schema")
    if source.get("decision") != "offline_paper_certificate_registry_snapshot_verified":
        raise RegistrySnapshotSealError("source decision invalid")
    if source.get("verification_scope") != "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_VERIFICATION_ONLY":
        raise RegistrySnapshotSealError("source verification scope invalid")
    if source.get("verification_state") != "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT":
        raise RegistrySnapshotSealError("source verification state invalid")
    if source.get("snapshot_verified") is not True:
        raise RegistrySnapshotSealError("snapshot verification incomplete")

    observed = source.get("offline_paper_certificate_registry_snapshot_verification_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_certificate_registry_snapshot_verification_sha256", None)
    if observed != sha256_of(clone):
        raise RegistrySnapshotSealError("snapshot verification integrity failed")

    for field, hash_field in (
        ("verified_snapshot_index", "verified_snapshot_index_sha256"),
        ("verification_checks", "verification_checks_sha256"),
        ("verification_ledger", "verification_ledger_sha256"),
    ):
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise RegistrySnapshotSealError(f"{field} integrity failed")

    verification_id = source.get("certificate_registry_snapshot_verification_id")
    snapshot_id = source.get("certificate_registry_snapshot_id")
    registry_verification_id = source.get("certificate_registry_verification_id")
    registry_id = source.get("certificate_registry_id")

    if not isinstance(verification_id, str) or not verification_id.startswith("CRSX-"):
        raise RegistrySnapshotSealError("snapshot verification id invalid")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("CRSN-"):
        raise RegistrySnapshotSealError("snapshot id invalid")
    if not isinstance(registry_verification_id, str) or not registry_verification_id.startswith("FCRX-"):
        raise RegistrySnapshotSealError("registry verification id invalid")
    if not isinstance(registry_id, str) or not registry_id.startswith("FCRS-"):
        raise RegistrySnapshotSealError("registry id invalid")

    index = source.get("verified_snapshot_index")
    if not isinstance(index, list) or not index:
        raise RegistrySnapshotSealError("verified snapshot index required")
    if source.get("verified_snapshot_receipt_count") != len(index):
        raise RegistrySnapshotSealError("verified snapshot receipt count mismatch")

    seen = set()
    for i, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise RegistrySnapshotSealError("verified snapshot index item invalid")
        if item.get("verification_record_index") != i:
            raise RegistrySnapshotSealError("verified snapshot index sequence invalid")

        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-"):
            raise RegistrySnapshotSealError("receipt id invalid")
        if receipt_id in seen:
            raise RegistrySnapshotSealError("duplicate receipt id")
        seen.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise RegistrySnapshotSealError("quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise RegistrySnapshotSealError("price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise RegistrySnapshotSealError("notional invalid")
        if item.get("verification_state") != "VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_SEALED_ARCHIVED_OFFLINE_RECEIPT":
            raise RegistrySnapshotSealError("verified snapshot receipt state invalid")

    if len(source.get("verification_checks", [])) != 12:
        raise RegistrySnapshotSealError("verification checks invalid")
    if len(source.get("verification_ledger", [])) != 6:
        raise RegistrySnapshotSealError("verification ledger invalid")

    gate = source.get("verification_gate", {})
    expected_gate = {
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
        "next_version": VERSION,
    }
    for key, value in expected_gate.items():
        if gate.get(key) != value:
            raise RegistrySnapshotSealError(f"verification_gate {key} invalid")

    for key in (
        "settlements_created",
        "positions_updated",
        "cash_updates_created",
        "portfolio_updates_created",
        "external_orders_submitted",
        "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise RegistrySnapshotSealError(f"mutation detected: {key}")

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
            raise RegistrySnapshotSealError(f"unsafe source state: {key}")

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise RegistrySnapshotSealError("safety lock invalid")

    return index


def build_seal(
    source: Dict[str, Any],
    config: Dict[str, Any],
    sealed_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    when = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if sealed_at is None
        else parse_timestamp(sealed_at)
    )

    seal_seed = (
        f"{source['certificate_registry_snapshot_verification_id']}|"
        f"{source['offline_paper_certificate_registry_snapshot_verification_sha256']}|"
        f"{when}|{VERSION}"
    )
    seal_id = "CRSS-" + hashlib.sha256(
        seal_seed.encode("utf-8")
    ).hexdigest()[:16].upper()

    manifest = {
        "seal_id": seal_id,
        "snapshot_verification_id": source["certificate_registry_snapshot_verification_id"],
        "snapshot_id": source["certificate_registry_snapshot_id"],
        "registry_verification_id": source["certificate_registry_verification_id"],
        "registry_id": source["certificate_registry_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "sealed_receipt_count": len(index),
        "seal_effect": "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY",
        "seal_state": "SEALED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT",
        "sealed_at": when,
    }

    sealed_index = [
        {
            "seal_record_index": i,
            "verification_record_index": item["verification_record_index"],
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
            "seal_state": "SEALED_VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT",
        }
        for i, item in enumerate(index, 1)
    ]

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate(
            (
                ("SNAPSHOT_VERIFICATION_INTEGRITY", "PASS"),
                ("VERIFIED_SNAPSHOT_INDEX_INTEGRITY", "PASS"),
                ("VERIFICATION_CHECKS_INTEGRITY", "PASS"),
                ("VERIFICATION_LEDGER_INTEGRITY", "PASS"),
                ("SEAL_ID_DETERMINISTIC", "PASS"),
                ("SEAL_MANIFEST_CREATED", "PASS"),
                ("SEALED_SNAPSHOT_INDEX_CREATED", "PASS"),
                ("RECEIPT_LINKAGES_AND_NOTIONALS_PRESERVED", "PASS"),
                ("SEAL_CONTENT_IMMUTABLE", "LOCKED"),
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
            "seal_id": seal_id,
        }
        for i, (event, state) in enumerate(
            (
                ("SNAPSHOT_VERIFICATION_ACCEPTED", "PASS"),
                ("SEAL_MANIFEST_CREATED", "CREATED"),
                ("VERIFIED_SNAPSHOT_INDEX_SEALED", "SEALED"),
                ("SEAL_CONTENT_LOCKED", "LOCKED"),
                ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT", "ENFORCED"),
                ("OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_COMPLETED", "SEALED"),
            ),
            1,
        )
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_certificate_registry_snapshot_sealed",
        "certificate_registry_snapshot_seal_id": seal_id,
        "certificate_registry_snapshot_verification_id": source["certificate_registry_snapshot_verification_id"],
        "certificate_registry_snapshot_id": source["certificate_registry_snapshot_id"],
        "certificate_registry_verification_id": source["certificate_registry_verification_id"],
        "certificate_registry_id": source["certificate_registry_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "seal_scope": "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY",
        "seal_state": "SEALED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT",
        "sealed_at": when,
        "seal_manifest": manifest,
        "seal_manifest_sha256": sha256_of(manifest),
        "sealed_receipt_count": len(sealed_index),
        "sealed_snapshot_index": sealed_index,
        "sealed_snapshot_index_sha256": sha256_of(sealed_index),
        "seal_checks": checks,
        "seal_checks_sha256": sha256_of(checks),
        "seal_ledger": ledger,
        "seal_ledger_sha256": sha256_of(ledger),
        "seal_gate": {
            "certificate_registry_snapshot_sealed": True,
            "seal_immutable": True,
            "seal_effect": "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY",
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AV",
        },
        "source_snapshot_verification_sha256": source["offline_paper_certificate_registry_snapshot_verification_sha256"],
        "source_verified_snapshot_index_sha256": source["verified_snapshot_index_sha256"],
        "source_verification_checks_sha256": source["verification_checks_sha256"],
        "source_verification_ledger_sha256": source["verification_ledger_sha256"],
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

    output["offline_paper_certificate_registry_snapshot_seal_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_seal_v75_2au.json": output,
        "registry_snapshot_seal_manifest_v75_2au.json": {
            "seal_id": output["certificate_registry_snapshot_seal_id"],
            "seal_manifest": output["seal_manifest"],
            "seal_manifest_sha256": output["seal_manifest_sha256"],
        },
        "sealed_snapshot_index_v75_2au.json": {
            "seal_id": output["certificate_registry_snapshot_seal_id"],
            "sealed_receipt_count": output["sealed_receipt_count"],
            "sealed_snapshot_index": output["sealed_snapshot_index"],
            "sealed_snapshot_index_sha256": output["sealed_snapshot_index_sha256"],
        },
        "registry_snapshot_seal_ledger_v75_2au.json": {
            "seal_id": output["certificate_registry_snapshot_seal_id"],
            "seal_ledger": output["seal_ledger"],
            "seal_ledger_sha256": output["seal_ledger_sha256"],
        },
    }

    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (output_dir / "registry_snapshot_seal_v75_2au.sha256").write_text(
        output["offline_paper_certificate_registry_snapshot_seal_sha256"] + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--sealed-at")
    args = parser.parse_args(argv)

    try:
        output = build_seal(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.sealed_at,
        )
        write_outputs(output, Path(args.output_dir))

        keys = (
            "status",
            "decision",
            "certificate_registry_snapshot_seal_id",
            "seal_state",
            "sealed_receipt_count",
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
            "network_used",
            "approved_for_live",
            "offline_paper_certificate_registry_snapshot_seal_sha256",
        )
        print(json.dumps({key: output[key] for key in keys}, indent=2, sort_keys=True))
        return 0

    except (
        RegistrySnapshotSealError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "decision": "offline_paper_certificate_registry_snapshot_seal_failed",
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
