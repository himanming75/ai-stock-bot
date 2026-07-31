from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2BB"
SCHEMA = (
    "v75.2bb.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal_verification.1"
)
SOURCE_VERSION = "75.2BA"
SOURCE_SCHEMA = (
    "v75.2ba.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal.1"
)


class RegistrySnapshotSealCertificateArchiveSealVerificationError(ValueError):
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
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            f"file not found: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "top-level JSON must be an object"
        )
    return data


def validate_config(config: Dict[str, Any]) -> None:
    expected_scope = (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL_VERIFICATION_ONLY"
    )
    if config.get("verification_scope") != expected_scope:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "verification_scope invalid"
        )

    required_true = (
        "require_archive_seal_integrity",
        "require_archive_seal_manifest_integrity",
        "require_sealed_archived_certified_snapshot_index_integrity",
        "require_archive_seal_checks_integrity",
        "require_archive_seal_ledger_integrity",
        "require_deterministic_archive_seal_id",
        "require_receipt_linkage_and_notional_preservation",
        "require_zero_settlement_and_account_mutations",
        "create_verified_sealed_archived_certified_snapshot_index",
        "create_archive_seal_verification_checks",
        "create_archive_seal_verification_ledger",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
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
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                f"{key} must be false"
            )


def expected_archive_seal_id(source: Dict[str, Any]) -> str:
    seed = (
        f"{source['certificate_registry_snapshot_seal_certificate_archive_verification_id']}|"
        f"{source['source_archive_verification_sha256']}|"
        f"{source['sealed_at']}|{SOURCE_VERSION}"
    )
    return "CRSCAS-" + hashlib.sha256(
        seed.encode("utf-8")
    ).hexdigest()[:16].upper()


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "source status must be PASS"
        )
    if source.get("version") != SOURCE_VERSION:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "unsupported source version"
        )
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "unsupported source schema"
        )
    if source.get("decision") != (
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_sealed"
    ):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "source decision invalid"
        )
    if source.get("seal_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL_ONLY"
    ):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "seal scope invalid"
        )
    if source.get("seal_state") != (
        "SEALED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
        "CERTIFICATE_ARCHIVE"
    ):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "seal state invalid"
        )

    observed = source.get(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_sha256"
    )
    clone = copy.deepcopy(source)
    clone.pop(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_sha256",
        None,
    )
    if observed != sha256_of(clone):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "archive seal integrity failed"
        )

    for field, hash_field in (
        ("archive_seal_manifest", "archive_seal_manifest_sha256"),
        (
            "sealed_archived_certified_snapshot_index",
            "sealed_archived_certified_snapshot_index_sha256",
        ),
        ("archive_seal_checks", "archive_seal_checks_sha256"),
        ("archive_seal_ledger", "archive_seal_ledger_sha256"),
    ):
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                f"{field} integrity failed"
            )

    archive_seal_id = source.get(
        "certificate_registry_snapshot_seal_certificate_archive_seal_id"
    )
    if (
        not isinstance(archive_seal_id, str)
        or not archive_seal_id.startswith("CRSCAS-")
    ):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "archive seal id invalid"
        )
    if archive_seal_id != expected_archive_seal_id(source):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "archive seal id is not deterministic"
        )

    identifiers = (
        (
            source.get(
                "certificate_registry_snapshot_seal_certificate_"
                "archive_verification_id"
            ),
            "CRSCAX-",
            "archive verification id",
        ),
        (
            source.get(
                "certificate_registry_snapshot_seal_certificate_archive_id"
            ),
            "CRSCA-",
            "archive id",
        ),
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
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                f"{label} invalid"
            )

    manifest = source.get("archive_seal_manifest")
    if not isinstance(manifest, dict):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "archive seal manifest required"
        )

    expected_manifest = {
        "archive_seal_id": archive_seal_id,
        "archive_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_"
            "archive_verification_id"
        ],
        "archive_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_id"
        ],
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
        "sealed_archived_receipt_count": source[
            "sealed_archived_receipt_count"
        ],
        "seal_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL_ONLY"
        ),
        "seal_state": (
            "SEALED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE"
        ),
        "sealed_at": source["sealed_at"],
    }
    if manifest != expected_manifest:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "archive seal manifest content invalid"
        )

    index = source.get("sealed_archived_certified_snapshot_index")
    if not isinstance(index, list) or not index:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "sealed archived certified snapshot index required"
        )
    if source.get("sealed_archived_receipt_count") != len(index):
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "sealed archived receipt count mismatch"
        )

    seen_receipts = set()
    for i, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "archive seal index item invalid"
            )
        if item.get("archive_seal_record_index") != i:
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "archive seal index sequence invalid"
            )

        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-"):
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "receipt id invalid"
            )
        if receipt_id in seen_receipts:
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "duplicate receipt id"
            )
        seen_receipts.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity <= 0
        ):
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "filled quantity invalid"
            )
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "fill price invalid"
            )
        if float(price) <= 0:
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "fill price invalid"
            )
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "notional value invalid"
            )
        if item.get("archive_seal_state") != (
            "SEALED_VERIFIED_ARCHIVED_CERTIFIED_SEALED_SNAPSHOTTED_"
            "REGISTERED_OFFLINE_RECEIPT"
        ):
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                "sealed archived receipt state invalid"
            )

    if len(source.get("archive_seal_checks", [])) != 12:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "archive seal checks invalid"
        )
    if len(source.get("archive_seal_ledger", [])) != 6:
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "archive seal ledger invalid"
        )

    gate = source.get("seal_gate", {})
    expected_gate = {
        "certificate_registry_snapshot_seal_certificate_archive_sealed": True,
        "archive_seal_immutable": True,
        "seal_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL_ONLY"
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
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                f"seal_gate {key} invalid"
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
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
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
            raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
                f"unsafe source state: {key}"
            )

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise RegistrySnapshotSealCertificateArchiveSealVerificationError(
            "safety lock invalid"
        )

    return index


def verify_archive_seal(
    source: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    verification_seed = (
        f"{source['certificate_registry_snapshot_seal_certificate_archive_seal_id']}|"
        f"{source['offline_paper_certificate_registry_snapshot_seal_certificate_archive_seal_sha256']}|"
        f"{VERSION}"
    )
    verification_id = "CRSCASX-" + hashlib.sha256(
        verification_seed.encode("utf-8")
    ).hexdigest()[:16].upper()

    verified_index = [
        {
            "archive_seal_verification_record_index": i,
            "archive_seal_record_index": item["archive_seal_record_index"],
            "archive_verification_record_index": item[
                "archive_verification_record_index"
            ],
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
            "archive_seal_verification_state": (
                "VERIFIED_SEALED_ARCHIVED_CERTIFIED_SEALED_SNAPSHOTTED_"
                "REGISTERED_OFFLINE_RECEIPT"
            ),
        }
        for i, item in enumerate(index, 1)
    ]

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate(
            (
                ("ARCHIVE_SEAL_INTEGRITY", "PASS"),
                ("ARCHIVE_SEAL_MANIFEST_INTEGRITY", "PASS"),
                ("SEALED_ARCHIVED_CERTIFIED_INDEX_INTEGRITY", "PASS"),
                ("ARCHIVE_SEAL_CHECKS_INTEGRITY", "PASS"),
                ("ARCHIVE_SEAL_LEDGER_INTEGRITY", "PASS"),
                ("DETERMINISTIC_ARCHIVE_SEAL_ID", "PASS"),
                ("RECEIPT_LINKAGE_PRESERVED", "PASS"),
                ("NOTIONAL_VALUES_PRESERVED", "PASS"),
                ("ARCHIVE_SEAL_IMMUTABILITY", "LOCKED"),
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
            "archive_seal_verification_id": verification_id,
        }
        for i, (event, state) in enumerate(
            (
                ("SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_SEAL_ACCEPTED", "PASS"),
                ("ARCHIVE_SEAL_MANIFEST_VERIFIED", "VERIFIED"),
                ("SEALED_ARCHIVED_CERTIFIED_INDEX_VERIFIED", "VERIFIED"),
                ("ARCHIVE_SEAL_EVIDENCE_LOCK_CONFIRMED", "LOCKED"),
                (
                    "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT",
                    "ENFORCED",
                ),
                (
                    "OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
                    "ARCHIVE_SEAL_VERIFICATION_COMPLETED",
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
            "archive_seal_verified"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_seal_verification_id": (
            verification_id
        ),
        "certificate_registry_snapshot_seal_certificate_archive_seal_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_seal_id"
        ],
        "certificate_registry_snapshot_seal_certificate_archive_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_"
            "archive_verification_id"
        ],
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
            "ARCHIVE_SEAL_VERIFICATION_ONLY"
        ),
        "verification_state": (
            "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL"
        ),
        "archive_seal_verified": True,
        "verified_sealed_archived_receipt_count": len(verified_index),
        "verified_sealed_archived_certified_snapshot_index": verified_index,
        "verified_sealed_archived_certified_snapshot_index_sha256": sha256_of(
            verified_index
        ),
        "archive_seal_verification_checks": checks,
        "archive_seal_verification_checks_sha256": sha256_of(checks),
        "archive_seal_verification_ledger": ledger,
        "archive_seal_verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "certificate_registry_snapshot_seal_certificate_archive_seal_verified": True,
            "archive_seal_immutable": True,
            "verification_effect": (
                "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
                "CERTIFICATE_ARCHIVE_SEAL_VERIFICATION_ONLY"
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
            "next_version": "75.2BC",
        },
        "source_archive_seal_sha256": source[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_sha256"
        ],
        "source_archive_seal_manifest_sha256": source[
            "archive_seal_manifest_sha256"
        ],
        "source_sealed_archived_certified_snapshot_index_sha256": source[
            "sealed_archived_certified_snapshot_index_sha256"
        ],
        "source_archive_seal_checks_sha256": source[
            "archive_seal_checks_sha256"
        ],
        "source_archive_seal_ledger_sha256": source[
            "archive_seal_ledger_sha256"
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
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_verification_sha256"
    ] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_seal_certificate_archive_seal_verification_v75_2bb.json": output,
        "verified_sealed_archived_certified_snapshot_index_v75_2bb.json": {
            "archive_seal_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_"
                "archive_seal_verification_id"
            ],
            "verified_sealed_archived_receipt_count": output[
                "verified_sealed_archived_receipt_count"
            ],
            "verified_sealed_archived_certified_snapshot_index": output[
                "verified_sealed_archived_certified_snapshot_index"
            ],
            "verified_sealed_archived_certified_snapshot_index_sha256": output[
                "verified_sealed_archived_certified_snapshot_index_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_verification_checks_v75_2bb.json": {
            "archive_seal_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_"
                "archive_seal_verification_id"
            ],
            "archive_seal_verification_checks": output[
                "archive_seal_verification_checks"
            ],
            "archive_seal_verification_checks_sha256": output[
                "archive_seal_verification_checks_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_verification_ledger_v75_2bb.json": {
            "archive_seal_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_"
                "archive_seal_verification_id"
            ],
            "archive_seal_verification_ledger": output[
                "archive_seal_verification_ledger"
            ],
            "archive_seal_verification_ledger_sha256": output[
                "archive_seal_verification_ledger_sha256"
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
        / "registry_snapshot_seal_certificate_archive_seal_"
        "verification_v75_2bb.sha256"
    ).write_text(
        output[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_verification_sha256"
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
        output = verify_archive_seal(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
        )
        write_outputs(output, Path(args.output_dir))

        keys = (
            "status",
            "decision",
            (
                "certificate_registry_snapshot_seal_certificate_"
                "archive_seal_verification_id"
            ),
            "verification_state",
            "verified_sealed_archived_receipt_count",
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
                "archive_seal_verification_sha256"
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
        RegistrySnapshotSealCertificateArchiveSealVerificationError,
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
                        "certificate_archive_seal_verification_failed"
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
