from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AW"
SCHEMA = "v75.2aw.offline_paper_certificate_registry_snapshot_seal_certificate.1"
SOURCE_VERSION = "75.2AV"
SOURCE_SCHEMA = "v75.2av.offline_paper_certificate_registry_snapshot_seal_verification.1"


class RegistrySnapshotSealCertificateError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistrySnapshotSealCertificateError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistrySnapshotSealCertificateError(f"invalid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise RegistrySnapshotSealCertificateError("top-level JSON must be an object")
    return data


def parse_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise RegistrySnapshotSealCertificateError("certified_at invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RegistrySnapshotSealCertificateError(
            "certified_at must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        raise RegistrySnapshotSealCertificateError(
            "certified_at must include timezone"
        )
    return parsed.isoformat()


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("certificate_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_ONLY"
    ):
        raise RegistrySnapshotSealCertificateError("certificate_scope invalid")

    required_true = (
        "require_seal_verification_integrity",
        "require_verified_sealed_snapshot_index_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_zero_settlement_and_account_mutations",
        "create_certificate_manifest",
        "create_certified_sealed_snapshot_index",
        "create_certificate_checks",
        "create_certificate_ledger",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise RegistrySnapshotSealCertificateError(f"{key} must be true")

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
            raise RegistrySnapshotSealCertificateError(f"{key} must be false")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise RegistrySnapshotSealCertificateError("source status must be PASS")
    if source.get("version") != SOURCE_VERSION:
        raise RegistrySnapshotSealCertificateError("unsupported source version")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise RegistrySnapshotSealCertificateError("unsupported source schema")
    if source.get("decision") != (
        "offline_paper_certificate_registry_snapshot_seal_verified"
    ):
        raise RegistrySnapshotSealCertificateError("source decision invalid")
    if source.get("verification_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_VERIFICATION_ONLY"
    ):
        raise RegistrySnapshotSealCertificateError(
            "source verification scope invalid"
        )
    if source.get("verification_state") != (
        "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL"
    ):
        raise RegistrySnapshotSealCertificateError(
            "source verification state invalid"
        )
    if source.get("seal_verified") is not True:
        raise RegistrySnapshotSealCertificateError(
            "snapshot seal verification incomplete"
        )

    observed = source.get(
        "offline_paper_certificate_registry_snapshot_seal_verification_sha256"
    )
    clone = copy.deepcopy(source)
    clone.pop(
        "offline_paper_certificate_registry_snapshot_seal_verification_sha256",
        None,
    )
    if observed != sha256_of(clone):
        raise RegistrySnapshotSealCertificateError(
            "snapshot seal verification integrity failed"
        )

    for field, hash_field in (
        (
            "verified_sealed_snapshot_index",
            "verified_sealed_snapshot_index_sha256",
        ),
        ("verification_checks", "verification_checks_sha256"),
        ("verification_ledger", "verification_ledger_sha256"),
    ):
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise RegistrySnapshotSealCertificateError(
                f"{field} integrity failed"
            )

    seal_verification_id = source.get(
        "certificate_registry_snapshot_seal_verification_id"
    )
    seal_id = source.get("certificate_registry_snapshot_seal_id")
    snapshot_verification_id = source.get(
        "certificate_registry_snapshot_verification_id"
    )
    snapshot_id = source.get("certificate_registry_snapshot_id")
    registry_verification_id = source.get(
        "certificate_registry_verification_id"
    )
    registry_id = source.get("certificate_registry_id")

    identifiers = (
        (seal_verification_id, "CRSSX-", "seal verification id"),
        (seal_id, "CRSS-", "seal id"),
        (snapshot_verification_id, "CRSX-", "snapshot verification id"),
        (snapshot_id, "CRSN-", "snapshot id"),
        (registry_verification_id, "FCRX-", "registry verification id"),
        (registry_id, "FCRS-", "registry id"),
    )
    for value, prefix, label in identifiers:
        if not isinstance(value, str) or not value.startswith(prefix):
            raise RegistrySnapshotSealCertificateError(f"{label} invalid")

    index = source.get("verified_sealed_snapshot_index")
    if not isinstance(index, list) or not index:
        raise RegistrySnapshotSealCertificateError(
            "verified sealed snapshot index required"
        )
    if source.get("verified_sealed_receipt_count") != len(index):
        raise RegistrySnapshotSealCertificateError(
            "verified sealed receipt count mismatch"
        )

    seen_receipts = set()
    for i, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise RegistrySnapshotSealCertificateError(
                "verified sealed index item invalid"
            )
        if item.get("verification_record_index") != i:
            raise RegistrySnapshotSealCertificateError(
                "verified sealed index sequence invalid"
            )

        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-"):
            raise RegistrySnapshotSealCertificateError("receipt id invalid")
        if receipt_id in seen_receipts:
            raise RegistrySnapshotSealCertificateError("duplicate receipt id")
        seen_receipts.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise RegistrySnapshotSealCertificateError(
                "filled quantity invalid"
            )
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise RegistrySnapshotSealCertificateError("fill price invalid")
        if float(price) <= 0:
            raise RegistrySnapshotSealCertificateError("fill price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise RegistrySnapshotSealCertificateError(
                "notional value invalid"
            )
        if item.get("verification_state") != (
            "VERIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_"
            "OFFLINE_RECEIPT"
        ):
            raise RegistrySnapshotSealCertificateError(
                "verified sealed receipt state invalid"
            )

    if len(source.get("verification_checks", [])) != 12:
        raise RegistrySnapshotSealCertificateError(
            "verification checks invalid"
        )
    if len(source.get("verification_ledger", [])) != 6:
        raise RegistrySnapshotSealCertificateError(
            "verification ledger invalid"
        )

    gate = source.get("verification_gate", {})
    expected_gate = {
        "certificate_registry_snapshot_seal_verified": True,
        "seal_immutable": True,
        "verification_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "VERIFICATION_ONLY"
        ),
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
            raise RegistrySnapshotSealCertificateError(
                f"verification_gate {key} invalid"
            )

    for key in (
        "settlements_created",
        "positions_updated",
        "cash_updates_created",
        "portfolio_updates_created",
        "external_orders_submitted",
        "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise RegistrySnapshotSealCertificateError(
                f"mutation detected: {key}"
            )

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
            raise RegistrySnapshotSealCertificateError(
                f"unsafe source state: {key}"
            )

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise RegistrySnapshotSealCertificateError("safety lock invalid")

    return index


def build_certificate(
    source: Dict[str, Any],
    config: Dict[str, Any],
    certified_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    when = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if certified_at is None
        else parse_timestamp(certified_at)
    )

    certificate_seed = (
        f"{source['certificate_registry_snapshot_seal_verification_id']}|"
        f"{source['offline_paper_certificate_registry_snapshot_seal_verification_sha256']}|"
        f"{when}|{VERSION}"
    )
    certificate_id = "CRSC-" + hashlib.sha256(
        certificate_seed.encode("utf-8")
    ).hexdigest()[:16].upper()

    manifest = {
        "certificate_id": certificate_id,
        "seal_verification_id": source[
            "certificate_registry_snapshot_seal_verification_id"
        ],
        "seal_id": source["certificate_registry_snapshot_seal_id"],
        "snapshot_verification_id": source[
            "certificate_registry_snapshot_verification_id"
        ],
        "snapshot_id": source["certificate_registry_snapshot_id"],
        "registry_verification_id": source[
            "certificate_registry_verification_id"
        ],
        "registry_id": source["certificate_registry_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "certified_receipt_count": len(index),
        "certificate_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ONLY"
        ),
        "certificate_state": (
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL"
        ),
        "certified_at": when,
    }

    certified_index = [
        {
            "certificate_record_index": i,
            "verification_record_index": item["verification_record_index"],
            "seal_record_index": item["seal_record_index"],
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
            "certificate_state": (
                "CERTIFIED_VERIFIED_SEALED_SNAPSHOTTED_REGISTERED_ARCHIVED_"
                "OFFLINE_RECEIPT"
            ),
        }
        for i, item in enumerate(index, 1)
    ]

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate(
            (
                ("SEAL_VERIFICATION_INTEGRITY", "PASS"),
                ("VERIFIED_SEALED_INDEX_INTEGRITY", "PASS"),
                ("VERIFICATION_CHECKS_INTEGRITY", "PASS"),
                ("VERIFICATION_LEDGER_INTEGRITY", "PASS"),
                ("CERTIFICATE_ID_DETERMINISTIC", "PASS"),
                ("CERTIFICATE_MANIFEST_CREATED", "PASS"),
                ("CERTIFIED_SEALED_INDEX_CREATED", "PASS"),
                ("RECEIPT_LINKAGES_AND_NOTIONALS_PRESERVED", "PASS"),
                ("CERTIFICATE_CONTENT_IMMUTABLE", "LOCKED"),
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
            "certificate_id": certificate_id,
        }
        for i, (event, state) in enumerate(
            (
                ("SNAPSHOT_SEAL_VERIFICATION_ACCEPTED", "PASS"),
                ("CERTIFICATE_MANIFEST_CREATED", "CREATED"),
                ("VERIFIED_SEALED_SNAPSHOT_INDEX_CERTIFIED", "CERTIFIED"),
                ("CERTIFICATE_CONTENT_LOCKED", "LOCKED"),
                (
                    "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT",
                    "ENFORCED",
                ),
                (
                    "OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
                    "COMPLETED",
                    "CERTIFIED",
                ),
            ),
            1,
        )
    ]

    output = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_created"
        ),
        "certificate_registry_snapshot_seal_certificate_id": certificate_id,
        "certificate_registry_snapshot_seal_verification_id": source[
            "certificate_registry_snapshot_seal_verification_id"
        ],
        "certificate_registry_snapshot_seal_id": source[
            "certificate_registry_snapshot_seal_id"
        ],
        "certificate_registry_snapshot_verification_id": source[
            "certificate_registry_snapshot_verification_id"
        ],
        "certificate_registry_snapshot_id": source[
            "certificate_registry_snapshot_id"
        ],
        "certificate_registry_verification_id": source[
            "certificate_registry_verification_id"
        ],
        "certificate_registry_id": source["certificate_registry_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "certificate_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_ONLY"
        ),
        "certificate_state": (
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL"
        ),
        "certified_at": when,
        "certificate_manifest": manifest,
        "certificate_manifest_sha256": sha256_of(manifest),
        "certified_receipt_count": len(certified_index),
        "certified_sealed_snapshot_index": certified_index,
        "certified_sealed_snapshot_index_sha256": sha256_of(certified_index),
        "certificate_checks": checks,
        "certificate_checks_sha256": sha256_of(checks),
        "certificate_ledger": ledger,
        "certificate_ledger_sha256": sha256_of(ledger),
        "certificate_gate": {
            "certificate_registry_snapshot_seal_certificate_created": True,
            "certificate_immutable": True,
            "certificate_effect": (
                "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
                "CERTIFICATE_ONLY"
            ),
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AX",
        },
        "source_seal_verification_sha256": source[
            "offline_paper_certificate_registry_snapshot_seal_verification_sha256"
        ],
        "source_verified_sealed_snapshot_index_sha256": source[
            "verified_sealed_snapshot_index_sha256"
        ],
        "source_verification_checks_sha256": source[
            "verification_checks_sha256"
        ],
        "source_verification_ledger_sha256": source[
            "verification_ledger_sha256"
        ],
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

    output[
        "offline_paper_certificate_registry_snapshot_seal_certificate_sha256"
    ] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_seal_certificate_v75_2aw.json": output,
        "registry_snapshot_seal_certificate_manifest_v75_2aw.json": {
            "certificate_id": output[
                "certificate_registry_snapshot_seal_certificate_id"
            ],
            "certificate_manifest": output["certificate_manifest"],
            "certificate_manifest_sha256": output[
                "certificate_manifest_sha256"
            ],
        },
        "certified_sealed_snapshot_index_v75_2aw.json": {
            "certificate_id": output[
                "certificate_registry_snapshot_seal_certificate_id"
            ],
            "certified_receipt_count": output["certified_receipt_count"],
            "certified_sealed_snapshot_index": output[
                "certified_sealed_snapshot_index"
            ],
            "certified_sealed_snapshot_index_sha256": output[
                "certified_sealed_snapshot_index_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_ledger_v75_2aw.json": {
            "certificate_id": output[
                "certificate_registry_snapshot_seal_certificate_id"
            ],
            "certificate_ledger": output["certificate_ledger"],
            "certificate_ledger_sha256": output["certificate_ledger_sha256"],
        },
    }

    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (
        output_dir / "registry_snapshot_seal_certificate_v75_2aw.sha256"
    ).write_text(
        output[
            "offline_paper_certificate_registry_snapshot_seal_certificate_sha256"
        ]
        + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--certified-at")
    args = parser.parse_args(argv)

    try:
        output = build_certificate(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.certified_at,
        )
        write_outputs(output, Path(args.output_dir))

        keys = (
            "status",
            "decision",
            "certificate_registry_snapshot_seal_certificate_id",
            "certificate_state",
            "certified_receipt_count",
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
            "network_used",
            "approved_for_live",
            "offline_paper_certificate_registry_snapshot_seal_certificate_sha256",
        )
        print(
            json.dumps(
                {key: output[key] for key in keys},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    except (
        RegistrySnapshotSealCertificateError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "decision": (
                        "offline_paper_certificate_registry_snapshot_seal_"
                        "certificate_failed"
                    ),
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
