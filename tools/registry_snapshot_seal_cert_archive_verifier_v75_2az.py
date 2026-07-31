from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AZ"
SCHEMA = "v75.2az.offline_paper_certificate_registry_snapshot_seal_certificate_archive_verification.1"
SOURCE_VERSION = "75.2AY"
SOURCE_SCHEMA = "v75.2ay.offline_paper_certificate_registry_snapshot_seal_certificate_archive.1"


class RegistrySnapshotSealCertificateArchiveVerificationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            f"file not found: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "top-level JSON must be an object"
        )
    return data


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("verification_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_VERIFICATION_ONLY"
    ):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "verification_scope invalid"
        )

    required_true = (
        "require_archive_integrity",
        "require_archive_manifest_integrity",
        "require_archived_certified_sealed_snapshot_index_integrity",
        "require_archive_checks_integrity",
        "require_archive_ledger_integrity",
        "require_deterministic_archive_id",
        "require_receipt_linkage_and_notional_preservation",
        "require_zero_settlement_and_account_mutations",
        "create_verified_archived_certified_sealed_snapshot_index",
        "create_archive_verification_checks",
        "create_archive_verification_ledger",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                f"{key} must be true"
            )

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
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                f"{key} must be false"
            )


def expected_archive_id(source: Dict[str, Any]) -> str:
    seed = (
        f"{source['certificate_registry_snapshot_seal_certificate_verification_id']}|"
        f"{source['source_certificate_verification_sha256']}|"
        f"{source['archived_at']}|{SOURCE_VERSION}"
    )
    return "CRSCA-" + hashlib.sha256(
        seed.encode("utf-8")
    ).hexdigest()[:16].upper()


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "source status must be PASS"
        )
    if source.get("version") != SOURCE_VERSION:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "unsupported source version"
        )
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "unsupported source schema"
        )
    if source.get("decision") != (
        "offline_paper_certificate_registry_snapshot_seal_certificate_archived"
    ):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "source decision invalid"
        )
    if source.get("archive_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_ONLY"
    ):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive scope invalid"
        )
    if source.get("archive_state") != (
        "ARCHIVED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE"
    ):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive state invalid"
        )

    observed = source.get(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_sha256"
    )
    clone = copy.deepcopy(source)
    clone.pop(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_sha256",
        None,
    )
    if observed != sha256_of(clone):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive integrity failed"
        )

    for field, hash_field in (
        ("archive_manifest", "archive_manifest_sha256"),
        (
            "archived_certified_sealed_snapshot_index",
            "archived_certified_sealed_snapshot_index_sha256",
        ),
        ("archive_checks", "archive_checks_sha256"),
        ("archive_ledger", "archive_ledger_sha256"),
    ):
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                f"{field} integrity failed"
            )

    archive_id = source.get(
        "certificate_registry_snapshot_seal_certificate_archive_id"
    )
    if not isinstance(archive_id, str) or not archive_id.startswith("CRSCA-"):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive id invalid"
        )
    if archive_id != expected_archive_id(source):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive id is not deterministic"
        )

    identifiers = (
        (
            source.get(
                "certificate_registry_snapshot_seal_certificate_verification_id"
            ),
            "CRSCX-",
            "certificate verification id",
        ),
        (
            source.get("certificate_registry_snapshot_seal_certificate_id"),
            "CRSC-",
            "certificate id",
        ),
        (
            source.get("certificate_registry_snapshot_seal_verification_id"),
            "CRSSX-",
            "seal verification id",
        ),
        (
            source.get("certificate_registry_snapshot_seal_id"),
            "CRSS-",
            "seal id",
        ),
        (
            source.get("certificate_registry_snapshot_verification_id"),
            "CRSX-",
            "snapshot verification id",
        ),
        (
            source.get("certificate_registry_snapshot_id"),
            "CRSN-",
            "snapshot id",
        ),
        (
            source.get("certificate_registry_verification_id"),
            "FCRX-",
            "registry verification id",
        ),
        (
            source.get("certificate_registry_id"),
            "FCRS-",
            "registry id",
        ),
    )
    for value, prefix, label in identifiers:
        if not isinstance(value, str) or not value.startswith(prefix):
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                f"{label} invalid"
            )

    manifest = source.get("archive_manifest")
    if not isinstance(manifest, dict):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive manifest required"
        )

    expected_manifest = {
        "archive_id": archive_id,
        "certificate_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_verification_id"
        ],
        "certificate_id": source[
            "certificate_registry_snapshot_seal_certificate_id"
        ],
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
        "archived_receipt_count": source["archived_receipt_count"],
        "archive_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_ONLY"
        ),
        "archive_state": (
            "ARCHIVED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE"
        ),
        "archived_at": source["archived_at"],
    }
    if manifest != expected_manifest:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive manifest content invalid"
        )

    index = source.get("archived_certified_sealed_snapshot_index")
    if not isinstance(index, list) or not index:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archived certified sealed snapshot index required"
        )
    if source.get("archived_receipt_count") != len(index):
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archived receipt count mismatch"
        )

    seen_receipts = set()
    for i, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "archive index item invalid"
            )
        if item.get("archive_record_index") != i:
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "archive index sequence invalid"
            )

        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-"):
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "receipt id invalid"
            )
        if receipt_id in seen_receipts:
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "duplicate receipt id"
            )
        seen_receipts.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "filled quantity invalid"
            )
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "fill price invalid"
            )
        if float(price) <= 0:
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "fill price invalid"
            )
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "notional value invalid"
            )
        if item.get("archive_state") != (
            "ARCHIVED_VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_"
            "OFFLINE_RECEIPT"
        ):
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                "archived receipt state invalid"
            )

    if len(source.get("archive_checks", [])) != 12:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive checks invalid"
        )
    if len(source.get("archive_ledger", [])) != 6:
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "archive ledger invalid"
        )

    gate = source.get("archive_gate", {})
    expected_gate = {
        "certificate_registry_snapshot_seal_certificate_archived": True,
        "archive_immutable": True,
        "archive_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_ONLY"
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
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                f"archive_gate {key} invalid"
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
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
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
            raise RegistrySnapshotSealCertificateArchiveVerificationError(
                f"unsafe source state: {key}"
            )

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise RegistrySnapshotSealCertificateArchiveVerificationError(
            "safety lock invalid"
        )

    return index


def verify_archive(
    source: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    verification_seed = (
        f"{source['certificate_registry_snapshot_seal_certificate_archive_id']}|"
        f"{source['offline_paper_certificate_registry_snapshot_seal_certificate_archive_sha256']}|"
        f"{VERSION}"
    )
    verification_id = "CRSCAX-" + hashlib.sha256(
        verification_seed.encode("utf-8")
    ).hexdigest()[:16].upper()

    verified_index = [
        {
            "archive_verification_record_index": i,
            "archive_record_index": item["archive_record_index"],
            "verification_record_index": item["verification_record_index"],
            "certificate_record_index": item["certificate_record_index"],
            "seal_verification_record_index": item[
                "seal_verification_record_index"
            ],
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
            "archive_verification_state": (
                "VERIFIED_ARCHIVED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_"
                "OFFLINE_RECEIPT"
            ),
        }
        for i, item in enumerate(index, 1)
    ]

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate(
            (
                ("ARCHIVE_INTEGRITY", "PASS"),
                ("ARCHIVE_MANIFEST_INTEGRITY", "PASS"),
                ("ARCHIVED_CERTIFIED_SEALED_INDEX_INTEGRITY", "PASS"),
                ("ARCHIVE_CHECKS_INTEGRITY", "PASS"),
                ("ARCHIVE_LEDGER_INTEGRITY", "PASS"),
                ("DETERMINISTIC_ARCHIVE_ID", "PASS"),
                ("RECEIPT_LINKAGE_PRESERVED", "PASS"),
                ("NOTIONAL_VALUES_PRESERVED", "PASS"),
                ("ARCHIVE_IMMUTABILITY", "LOCKED"),
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
            "archive_verification_id": verification_id,
        }
        for i, (event, state) in enumerate(
            (
                ("SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_ACCEPTED", "PASS"),
                ("ARCHIVE_MANIFEST_VERIFIED", "VERIFIED"),
                ("ARCHIVED_CERTIFIED_SEALED_INDEX_VERIFIED", "VERIFIED"),
                ("ARCHIVE_EVIDENCE_LOCK_CONFIRMED", "LOCKED"),
                (
                    "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT",
                    "ENFORCED",
                ),
                (
                    "OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
                    "ARCHIVE_VERIFICATION_COMPLETED",
                    "VERIFIED",
                ),
            ),
            1,
        )
    ]

    output = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_verified"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_verification_id": (
            verification_id
        ),
        "certificate_registry_snapshot_seal_certificate_archive_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_id"
        ],
        "certificate_registry_snapshot_seal_certificate_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_verification_id"
        ],
        "certificate_registry_snapshot_seal_certificate_id": source[
            "certificate_registry_snapshot_seal_certificate_id"
        ],
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
        "verification_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_VERIFICATION_ONLY"
        ),
        "verification_state": (
            "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE"
        ),
        "archive_verified": True,
        "verified_archived_receipt_count": len(verified_index),
        "verified_archived_certified_sealed_snapshot_index": verified_index,
        "verified_archived_certified_sealed_snapshot_index_sha256": sha256_of(
            verified_index
        ),
        "archive_verification_checks": checks,
        "archive_verification_checks_sha256": sha256_of(checks),
        "archive_verification_ledger": ledger,
        "archive_verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "certificate_registry_snapshot_seal_certificate_archive_verified": True,
            "archive_immutable": True,
            "verification_effect": (
                "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
                "CERTIFICATE_ARCHIVE_VERIFICATION_ONLY"
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
            "next_version": "75.2BA",
        },
        "source_archive_sha256": source[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_sha256"
        ],
        "source_archive_manifest_sha256": source["archive_manifest_sha256"],
        "source_archived_certified_sealed_snapshot_index_sha256": source[
            "archived_certified_sealed_snapshot_index_sha256"
        ],
        "source_archive_checks_sha256": source["archive_checks_sha256"],
        "source_archive_ledger_sha256": source["archive_ledger_sha256"],
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
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_verification_sha256"
    ] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_seal_certificate_archive_verification_v75_2az.json": (
            output
        ),
        "verified_archived_certified_sealed_snapshot_index_v75_2az.json": {
            "archive_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_"
                "archive_verification_id"
            ],
            "verified_archived_receipt_count": output[
                "verified_archived_receipt_count"
            ],
            "verified_archived_certified_sealed_snapshot_index": output[
                "verified_archived_certified_sealed_snapshot_index"
            ],
            "verified_archived_certified_sealed_snapshot_index_sha256": output[
                "verified_archived_certified_sealed_snapshot_index_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_verification_checks_v75_2az.json": {
            "archive_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_"
                "archive_verification_id"
            ],
            "archive_verification_checks": output[
                "archive_verification_checks"
            ],
            "archive_verification_checks_sha256": output[
                "archive_verification_checks_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_verification_ledger_v75_2az.json": {
            "archive_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_"
                "archive_verification_id"
            ],
            "archive_verification_ledger": output[
                "archive_verification_ledger"
            ],
            "archive_verification_ledger_sha256": output[
                "archive_verification_ledger_sha256"
            ],
        },
    }

    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (
        output_dir
        / "registry_snapshot_seal_certificate_archive_verification_v75_2az.sha256"
    ).write_text(
        output[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_verification_sha256"
        ]
        + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        output = verify_archive(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
        )
        write_outputs(output, Path(args.output_dir))

        keys = (
            "status",
            "decision",
            (
                "certificate_registry_snapshot_seal_certificate_"
                "archive_verification_id"
            ),
            "verification_state",
            "verified_archived_receipt_count",
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
            "network_used",
            "approved_for_live",
            (
                "offline_paper_certificate_registry_snapshot_seal_certificate_"
                "archive_verification_sha256"
            ),
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
        RegistrySnapshotSealCertificateArchiveVerificationError,
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
                        "certificate_archive_verification_failed"
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
