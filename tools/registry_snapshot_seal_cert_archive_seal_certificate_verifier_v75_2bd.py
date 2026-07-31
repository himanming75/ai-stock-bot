from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2BD"
SCHEMA = (
    "v75.2bd.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal_certificate_verification.1"
)
SOURCE_VERSION = "75.2BC"
SOURCE_SCHEMA = (
    "v75.2bc.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal_certificate.1"
)


class ArchiveSealCertificateVerificationError(ValueError):
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
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArchiveSealCertificateVerificationError(
            f"file not found: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ArchiveSealCertificateVerificationError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise ArchiveSealCertificateVerificationError(
            "top-level JSON must be an object"
        )
    return value


def validate_config(config: Dict[str, Any]) -> None:
    expected_scope = (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_ONLY"
    )
    if config.get("verification_scope") != expected_scope:
        raise ArchiveSealCertificateVerificationError(
            "verification_scope invalid"
        )

    required_true = (
        "require_archive_seal_certificate_integrity",
        "require_archive_seal_certificate_manifest_integrity",
        "require_certified_verified_sealed_archived_snapshot_index_integrity",
        "require_archive_seal_certificate_checks_integrity",
        "require_archive_seal_certificate_ledger_integrity",
        "require_deterministic_archive_seal_certificate_id",
        "require_receipt_linkage_and_notional_preservation",
        "require_zero_settlement_and_account_mutations",
        "create_verified_archive_seal_certificate_index",
        "create_archive_seal_certificate_verification_checks",
        "create_archive_seal_certificate_verification_ledger",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise ArchiveSealCertificateVerificationError(
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
            raise ArchiveSealCertificateVerificationError(
                f"{key} must be false"
            )


def expected_certificate_id(source: Dict[str, Any]) -> str:
    seed = (
        f"{source['certificate_registry_snapshot_seal_certificate_archive_seal_verification_id']}|"
        f"{source['source_archive_seal_verification_sha256']}|{SOURCE_VERSION}"
    )
    return "CRSCASC-" + hashlib.sha256(
        seed.encode("utf-8")
    ).hexdigest()[:16].upper()


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise ArchiveSealCertificateVerificationError(
            "source status must be PASS"
        )
    if source.get("version") != SOURCE_VERSION:
        raise ArchiveSealCertificateVerificationError(
            "unsupported source version"
        )
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise ArchiveSealCertificateVerificationError(
            "unsupported source schema"
        )
    if source.get("decision") != (
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_built"
    ):
        raise ArchiveSealCertificateVerificationError(
            "source decision invalid"
        )
    if source.get("certificate_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL_CERTIFICATE_ONLY"
    ):
        raise ArchiveSealCertificateVerificationError(
            "certificate scope invalid"
        )
    if source.get("archive_seal_certificate_state") != (
        "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
        "CERTIFICATE_ARCHIVE_SEAL"
    ):
        raise ArchiveSealCertificateVerificationError(
            "certificate state invalid"
        )

    observed = source.get(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_sha256"
    )
    clone = copy.deepcopy(source)
    clone.pop(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_sha256",
        None,
    )
    if observed != sha256_of(clone):
        raise ArchiveSealCertificateVerificationError(
            "archive seal certificate integrity failed"
        )

    component_pairs = (
        (
            "archive_seal_certificate_manifest",
            "archive_seal_certificate_manifest_sha256",
        ),
        (
            "certified_verified_sealed_archived_snapshot_index",
            "certified_verified_sealed_archived_snapshot_index_sha256",
        ),
        (
            "archive_seal_certificate_checks",
            "archive_seal_certificate_checks_sha256",
        ),
        (
            "archive_seal_certificate_ledger",
            "archive_seal_certificate_ledger_sha256",
        ),
    )
    for field, hash_field in component_pairs:
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise ArchiveSealCertificateVerificationError(
                f"{field} integrity failed"
            )

    certificate_id = source.get(
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_id"
    )
    if (
        not isinstance(certificate_id, str)
        or not certificate_id.startswith("CRSCASC-")
    ):
        raise ArchiveSealCertificateVerificationError(
            "archive seal certificate id invalid"
        )
    if certificate_id != expected_certificate_id(source):
        raise ArchiveSealCertificateVerificationError(
            "archive seal certificate id is not deterministic"
        )

    manifest = source.get("archive_seal_certificate_manifest")
    if not isinstance(manifest, dict):
        raise ArchiveSealCertificateVerificationError(
            "archive seal certificate manifest required"
        )

    expected_manifest = {
        "archive_seal_certificate_id": certificate_id,
        "archive_seal_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_"
            "seal_verification_id"
        ],
        "archive_seal_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_seal_id"
        ],
        "archive_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_"
            "archive_verification_id"
        ],
        "archive_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_id"
        ],
        "receipt_batch_id": source["receipt_batch_id"],
        "certified_archived_receipt_count": source[
            "certified_archived_receipt_count"
        ],
        "certificate_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL_CERTIFICATE_ONLY"
        ),
        "certificate_state": (
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL"
        ),
    }
    if manifest != expected_manifest:
        raise ArchiveSealCertificateVerificationError(
            "archive seal certificate manifest content invalid"
        )

    index = source.get(
        "certified_verified_sealed_archived_snapshot_index"
    )
    if not isinstance(index, list) or not index:
        raise ArchiveSealCertificateVerificationError(
            "certified archived snapshot index required"
        )
    if source.get("certified_archived_receipt_count") != len(index):
        raise ArchiveSealCertificateVerificationError(
            "certified archived receipt count mismatch"
        )

    receipt_ids = set()
    for i, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise ArchiveSealCertificateVerificationError(
                "certified archived index item invalid"
            )
        if item.get("archive_seal_certificate_record_index") != i:
            raise ArchiveSealCertificateVerificationError(
                "certificate index sequence invalid"
            )

        receipt_id = item.get("receipt_id")
        if (
            not isinstance(receipt_id, str)
            or not receipt_id.startswith("FRC-")
        ):
            raise ArchiveSealCertificateVerificationError(
                "receipt id invalid"
            )
        if receipt_id in receipt_ids:
            raise ArchiveSealCertificateVerificationError(
                "duplicate receipt id"
            )
        receipt_ids.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity <= 0
        ):
            raise ArchiveSealCertificateVerificationError(
                "filled quantity invalid"
            )
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or float(price) <= 0
        ):
            raise ArchiveSealCertificateVerificationError(
                "fill price invalid"
            )
        if item.get("notional_value") != round(
            float(price) * quantity, 10
        ):
            raise ArchiveSealCertificateVerificationError(
                "notional value invalid"
            )
        if item.get("archive_seal_certificate_state") != (
            "CERTIFIED_VERIFIED_SEALED_ARCHIVED_CERTIFIED_SEALED_"
            "SNAPSHOTTED_REGISTERED_OFFLINE_RECEIPT"
        ):
            raise ArchiveSealCertificateVerificationError(
                "archive seal certificate receipt state invalid"
            )

    if len(source.get("archive_seal_certificate_checks", [])) != 12:
        raise ArchiveSealCertificateVerificationError(
            "archive seal certificate checks invalid"
        )
    if len(source.get("archive_seal_certificate_ledger", [])) != 6:
        raise ArchiveSealCertificateVerificationError(
            "archive seal certificate ledger invalid"
        )

    gate = source.get("certificate_gate")
    if not isinstance(gate, dict):
        raise ArchiveSealCertificateVerificationError(
            "certificate gate required"
        )

    expected_gate = {
        "archive_seal_certificate_built": True,
        "archive_seal_certificate_immutable": True,
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
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise ArchiveSealCertificateVerificationError(
                f"certificate_gate {key} invalid"
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
            raise ArchiveSealCertificateVerificationError(
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
            raise ArchiveSealCertificateVerificationError(
                f"unsafe source state: {key}"
            )

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise ArchiveSealCertificateVerificationError(
            "safety lock invalid"
        )

    return index


def verify_archive_seal_certificate(
    source: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    certificate_id = source[
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_id"
    ]
    source_hash = source[
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_sha256"
    ]
    verification_id = "CRSCASCX-" + hashlib.sha256(
        f"{certificate_id}|{source_hash}|{VERSION}".encode("utf-8")
    ).hexdigest()[:16].upper()

    verified_index = [
        {
            "archive_seal_certificate_verification_record_index": i,
            **copy.deepcopy(item),
            "archive_seal_certificate_verification_state": (
                "VERIFIED_CERTIFIED_VERIFIED_SEALED_ARCHIVED_CERTIFIED_"
                "SEALED_SNAPSHOTTED_REGISTERED_OFFLINE_RECEIPT"
            ),
        }
        for i, item in enumerate(index, 1)
    ]

    checks = [
        {"check_index": i, "check": check, "state": state}
        for i, (check, state) in enumerate(
            (
                ("ARCHIVE_SEAL_CERTIFICATE_INTEGRITY", "PASS"),
                ("CERTIFICATE_MANIFEST_INTEGRITY", "PASS"),
                ("CERTIFIED_ARCHIVED_INDEX_INTEGRITY", "PASS"),
                ("CERTIFICATE_CHECKS_INTEGRITY", "PASS"),
                ("CERTIFICATE_LEDGER_INTEGRITY", "PASS"),
                ("DETERMINISTIC_CERTIFICATE_ID", "PASS"),
                ("RECEIPT_LINKAGE_PRESERVED", "PASS"),
                ("NOTIONAL_VALUES_PRESERVED", "PASS"),
                ("CERTIFICATE_IMMUTABILITY", "LOCKED"),
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
            "archive_seal_certificate_verification_id": verification_id,
        }
        for i, (event, state) in enumerate(
            (
                ("ARCHIVE_SEAL_CERTIFICATE_ACCEPTED", "PASS"),
                ("CERTIFICATE_MANIFEST_VERIFIED", "VERIFIED"),
                ("CERTIFIED_ARCHIVED_INDEX_VERIFIED", "VERIFIED"),
                ("CERTIFICATE_EVIDENCE_LOCK_CONFIRMED", "LOCKED"),
                (
                    "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT",
                    "ENFORCED",
                ),
                (
                    "ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_COMPLETED",
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
            "archive_seal_certificate_verified"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_verification_id": verification_id,
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_id": certificate_id,
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_"
            "seal_verification_id"
        ],
        "certificate_registry_snapshot_seal_certificate_archive_seal_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_seal_id"
        ],
        "certificate_registry_snapshot_seal_certificate_"
        "archive_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_"
            "archive_verification_id"
        ],
        "certificate_registry_snapshot_seal_certificate_archive_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_id"
        ],
        "receipt_batch_id": source["receipt_batch_id"],
        "verification_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_ONLY"
        ),
        "archive_seal_certificate_verification_state": (
            "VERIFIED_CERTIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL"
        ),
        "archive_seal_certificate_verified": True,
        "verified_certified_archived_receipt_count": len(verified_index),
        "verified_archive_seal_certificate_index": verified_index,
        "verified_archive_seal_certificate_index_sha256": sha256_of(
            verified_index
        ),
        "archive_seal_certificate_verification_checks": checks,
        "archive_seal_certificate_verification_checks_sha256": sha256_of(
            checks
        ),
        "archive_seal_certificate_verification_ledger": ledger,
        "archive_seal_certificate_verification_ledger_sha256": sha256_of(
            ledger
        ),
        "verification_gate": {
            "archive_seal_certificate_verified": True,
            "archive_seal_certificate_immutable": True,
            "verification_effect": (
                "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
                "CERTIFICATE_ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_ONLY"
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
            "next_version": "75.2BE",
        },
        "source_archive_seal_certificate_sha256": source_hash,
        "source_archive_seal_certificate_manifest_sha256": source[
            "archive_seal_certificate_manifest_sha256"
        ],
        "source_certified_verified_sealed_archived_snapshot_index_sha256": source[
            "certified_verified_sealed_archived_snapshot_index_sha256"
        ],
        "source_archive_seal_certificate_checks_sha256": source[
            "archive_seal_certificate_checks_sha256"
        ],
        "source_archive_seal_certificate_ledger_sha256": source[
            "archive_seal_certificate_ledger_sha256"
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
        "archive_seal_certificate_verification_sha256"
    ] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_seal_certificate_archive_seal_"
        "certificate_verification_v75_2bd.json": output,
        "verified_archive_seal_certificate_index_v75_2bd.json": {
            "archive_seal_certificate_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_archive_"
                "seal_certificate_verification_id"
            ],
            "verified_certified_archived_receipt_count": output[
                "verified_certified_archived_receipt_count"
            ],
            "verified_archive_seal_certificate_index": output[
                "verified_archive_seal_certificate_index"
            ],
            "verified_archive_seal_certificate_index_sha256": output[
                "verified_archive_seal_certificate_index_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_"
        "certificate_verification_checks_v75_2bd.json": {
            "archive_seal_certificate_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_archive_"
                "seal_certificate_verification_id"
            ],
            "archive_seal_certificate_verification_checks": output[
                "archive_seal_certificate_verification_checks"
            ],
            "archive_seal_certificate_verification_checks_sha256": output[
                "archive_seal_certificate_verification_checks_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_"
        "certificate_verification_ledger_v75_2bd.json": {
            "archive_seal_certificate_verification_id": output[
                "certificate_registry_snapshot_seal_certificate_archive_"
                "seal_certificate_verification_id"
            ],
            "archive_seal_certificate_verification_ledger": output[
                "archive_seal_certificate_verification_ledger"
            ],
            "archive_seal_certificate_verification_ledger_sha256": output[
                "archive_seal_certificate_verification_ledger_sha256"
            ],
        },
    }

    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        output = verify_archive_seal_certificate(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
        )
        write_outputs(output, Path(args.output_dir))

        keys = (
            "status",
            "decision",
            (
                "certificate_registry_snapshot_seal_certificate_archive_"
                "seal_certificate_verification_id"
            ),
            "archive_seal_certificate_verification_state",
            "verified_certified_archived_receipt_count",
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
                "archive_seal_certificate_verification_sha256"
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
        ArchiveSealCertificateVerificationError,
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
                        "certificate_archive_seal_certificate_"
                        "verification_failed"
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
