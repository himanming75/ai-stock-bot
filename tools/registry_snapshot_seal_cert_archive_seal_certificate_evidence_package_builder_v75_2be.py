from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2BE"
SCHEMA = (
    "v75.2be.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal_certificate_evidence_package.1"
)
SOURCE_VERSION = "75.2BD"
SOURCE_SCHEMA = (
    "v75.2bd.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal_certificate_verification.1"
)


class EvidencePackageBuilderError(ValueError):
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
        raise EvidencePackageBuilderError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidencePackageBuilderError(f"invalid JSON: {path}") from exc

    if not isinstance(value, dict):
        raise EvidencePackageBuilderError("top-level JSON must be an object")
    return value


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("package_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL_CERTIFICATE_EVIDENCE_PACKAGE_ONLY"
    ):
        raise EvidencePackageBuilderError("package_scope invalid")

    for key in (
        "require_archive_seal_certificate_verification_integrity",
        "require_verified_certificate_index_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_deterministic_evidence_package_id",
        "require_receipt_linkage_and_notional_preservation",
        "require_zero_settlement_and_account_mutations",
        "create_evidence_package_manifest",
        "create_evidence_component_hash_map",
        "create_packaged_verified_certificate_index",
        "create_evidence_package_checks",
        "create_evidence_package_ledger",
    ):
        if config.get(key) is not True:
            raise EvidencePackageBuilderError(f"{key} must be true")

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
        "external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise EvidencePackageBuilderError(f"{key} must be false")


def expected_source_verification_id(source: Dict[str, Any]) -> str:
    certificate_id = source[
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_id"
    ]
    source_hash = source["source_archive_seal_certificate_sha256"]
    return "CRSCASCX-" + hashlib.sha256(
        f"{certificate_id}|{source_hash}|{SOURCE_VERSION}".encode("utf-8")
    ).hexdigest()[:16].upper()


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise EvidencePackageBuilderError("source status must be PASS")
    if source.get("version") != SOURCE_VERSION:
        raise EvidencePackageBuilderError("unsupported source version")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise EvidencePackageBuilderError("unsupported source schema")
    if source.get("decision") != (
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_verified"
    ):
        raise EvidencePackageBuilderError("source decision invalid")
    if source.get("verification_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_ONLY"
    ):
        raise EvidencePackageBuilderError("verification scope invalid")
    if source.get("archive_seal_certificate_verification_state") != (
        "VERIFIED_CERTIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
        "CERTIFICATE_ARCHIVE_SEAL"
    ):
        raise EvidencePackageBuilderError("verification state invalid")
    if source.get("archive_seal_certificate_verified") is not True:
        raise EvidencePackageBuilderError("certificate must be verified")

    observed = source.get(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_verification_sha256"
    )
    clone = copy.deepcopy(source)
    clone.pop(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_verification_sha256",
        None,
    )
    if observed != sha256_of(clone):
        raise EvidencePackageBuilderError(
            "archive seal certificate verification integrity failed"
        )

    verification_id = source.get(
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_verification_id"
    )
    if verification_id != expected_source_verification_id(source):
        raise EvidencePackageBuilderError(
            "source verification id is not deterministic"
        )

    component_pairs = (
        (
            "verified_archive_seal_certificate_index",
            "verified_archive_seal_certificate_index_sha256",
        ),
        (
            "archive_seal_certificate_verification_checks",
            "archive_seal_certificate_verification_checks_sha256",
        ),
        (
            "archive_seal_certificate_verification_ledger",
            "archive_seal_certificate_verification_ledger_sha256",
        ),
    )
    for field, hash_field in component_pairs:
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise EvidencePackageBuilderError(f"{field} integrity failed")

    index = source.get("verified_archive_seal_certificate_index")
    if not isinstance(index, list) or not index:
        raise EvidencePackageBuilderError(
            "verified archive seal certificate index required"
        )
    if source.get("verified_certified_archived_receipt_count") != len(index):
        raise EvidencePackageBuilderError("verified receipt count mismatch")

    seen_receipts = set()
    for i, item in enumerate(index, 1):
        if item.get(
            "archive_seal_certificate_verification_record_index"
        ) != i:
            raise EvidencePackageBuilderError("verified index sequence invalid")
        receipt_id = item.get("receipt_id")
        if (
            not isinstance(receipt_id, str)
            or not receipt_id.startswith("FRC-")
            or receipt_id in seen_receipts
        ):
            raise EvidencePackageBuilderError(
                "receipt linkage invalid or duplicate"
            )
        seen_receipts.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity <= 0
        ):
            raise EvidencePackageBuilderError("filled quantity invalid")
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or float(price) <= 0
        ):
            raise EvidencePackageBuilderError("fill price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise EvidencePackageBuilderError("notional value invalid")

    if len(source.get(
        "archive_seal_certificate_verification_checks", []
    )) != 12:
        raise EvidencePackageBuilderError("verification checks invalid")
    if len(source.get(
        "archive_seal_certificate_verification_ledger", []
    )) != 6:
        raise EvidencePackageBuilderError("verification ledger invalid")

    gate = source.get("verification_gate")
    if not isinstance(gate, dict):
        raise EvidencePackageBuilderError("verification gate required")
    if gate.get("archive_seal_certificate_verified") is not True:
        raise EvidencePackageBuilderError(
            "verification gate certificate state invalid"
        )
    if gate.get("archive_seal_certificate_immutable") is not True:
        raise EvidencePackageBuilderError(
            "verification gate immutability invalid"
        )
    if gate.get("next_version") != VERSION:
        raise EvidencePackageBuilderError(
            "verification gate next version invalid"
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
            raise EvidencePackageBuilderError(f"mutation detected: {key}")

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
            raise EvidencePackageBuilderError(f"unsafe source state: {key}")

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise EvidencePackageBuilderError("safety lock invalid")

    return index


def build_evidence_package(
    source: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    source_verification_id = source[
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_verification_id"
    ]
    source_verification_hash = source[
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_verification_sha256"
    ]
    package_id = "CRSCASCEP-" + hashlib.sha256(
        f"{source_verification_id}|{source_verification_hash}|{VERSION}".encode(
            "utf-8"
        )
    ).hexdigest()[:16].upper()

    packaged_index = [
        {
            "evidence_package_record_index": i,
            **copy.deepcopy(item),
            "evidence_package_state": (
                "PACKAGED_VERIFIED_CERTIFIED_VERIFIED_SEALED_ARCHIVED_"
                "CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_OFFLINE_RECEIPT"
            ),
        }
        for i, item in enumerate(index, 1)
    ]

    component_hash_map = {
        "source_archive_seal_certificate_verification_sha256":
            source_verification_hash,
        "source_archive_seal_certificate_sha256":
            source["source_archive_seal_certificate_sha256"],
        "source_archive_seal_certificate_manifest_sha256":
            source["source_archive_seal_certificate_manifest_sha256"],
        "source_certified_verified_sealed_archived_snapshot_index_sha256":
            source[
                "source_certified_verified_sealed_archived_snapshot_index_sha256"
            ],
        "source_archive_seal_certificate_checks_sha256":
            source["source_archive_seal_certificate_checks_sha256"],
        "source_archive_seal_certificate_ledger_sha256":
            source["source_archive_seal_certificate_ledger_sha256"],
        "source_verified_archive_seal_certificate_index_sha256":
            source["verified_archive_seal_certificate_index_sha256"],
        "source_archive_seal_certificate_verification_checks_sha256":
            source[
                "archive_seal_certificate_verification_checks_sha256"
            ],
        "source_archive_seal_certificate_verification_ledger_sha256":
            source[
                "archive_seal_certificate_verification_ledger_sha256"
            ],
    }

    manifest = {
        "evidence_package_id": package_id,
        "source_archive_seal_certificate_verification_id":
            source_verification_id,
        "archive_seal_certificate_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_"
            "seal_certificate_id"
        ],
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
        "packaged_verified_receipt_count": len(packaged_index),
        "component_count": len(component_hash_map),
        "package_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL_CERTIFICATE_EVIDENCE_PACKAGE_ONLY"
        ),
        "package_state": (
            "PACKAGED_VERIFIED_CERTIFIED_OFFLINE_CERTIFICATE_REGISTRY_"
            "SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_SEAL"
        ),
    }

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate(
            (
                ("SOURCE_VERIFICATION_INTEGRITY", "PASS"),
                ("DETERMINISTIC_EVIDENCE_PACKAGE_ID", "PASS"),
                ("EVIDENCE_PACKAGE_MANIFEST_CREATED", "PASS"),
                ("COMPONENT_HASH_MAP_CREATED", "PASS"),
                ("VERIFIED_CERTIFICATE_INDEX_PACKAGED", "PASS"),
                ("RECEIPT_LINKAGE_PRESERVED", "PASS"),
                ("NOTIONAL_VALUES_PRESERVED", "PASS"),
                ("SOURCE_EVIDENCE_IMMUTABLE", "LOCKED"),
                ("SETTLEMENT_MUTATIONS_ABSENT", "ENFORCED"),
                ("ACCOUNT_MUTATIONS_ABSENT", "ENFORCED"),
                ("NETWORK_AND_BROKER_DISABLED", "PASS"),
                ("LIVE_TRADING_PROHIBITED", "ENFORCED"),
            ),
            1,
        )
    ]

    ledger = [
        {
            "ledger_index": i,
            "event": event,
            "state": state,
            "evidence_package_id": package_id,
        }
        for i, (event, state) in enumerate(
            (
                ("CERTIFICATE_VERIFICATION_ACCEPTED", "PASS"),
                ("EVIDENCE_PACKAGE_MANIFEST_CREATED", "CREATED"),
                ("COMPONENT_HASH_MAP_LOCKED", "LOCKED"),
                ("VERIFIED_CERTIFICATE_INDEX_PACKAGED", "PACKAGED"),
                (
                    "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT",
                    "ENFORCED",
                ),
                ("EVIDENCE_PACKAGE_BUILD_COMPLETED", "PACKAGED"),
            ),
            1,
        )
    ]

    output = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_evidence_package_built"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_seal_"
        "certificate_evidence_package_id": package_id,
        "certificate_registry_snapshot_seal_certificate_archive_seal_"
        "certificate_verification_id": source_verification_id,
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_"
            "seal_certificate_id"
        ],
        "receipt_batch_id": source["receipt_batch_id"],
        "package_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_EVIDENCE_PACKAGE_ONLY"
        ),
        "evidence_package_state": (
            "PACKAGED_VERIFIED_CERTIFIED_OFFLINE_CERTIFICATE_REGISTRY_"
            "SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_SEAL"
        ),
        "evidence_package_manifest": manifest,
        "evidence_package_manifest_sha256": sha256_of(manifest),
        "evidence_component_hash_map": component_hash_map,
        "evidence_component_hash_map_sha256": sha256_of(component_hash_map),
        "packaged_verified_receipt_count": len(packaged_index),
        "packaged_verified_archive_seal_certificate_index": packaged_index,
        "packaged_verified_archive_seal_certificate_index_sha256":
            sha256_of(packaged_index),
        "evidence_package_checks": checks,
        "evidence_package_checks_sha256": sha256_of(checks),
        "evidence_package_ledger": ledger,
        "evidence_package_ledger_sha256": sha256_of(ledger),
        "package_gate": {
            "evidence_package_built": True,
            "evidence_package_immutable": True,
            "source_archive_seal_certificate_verified": True,
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2BF",
        },
        "source_archive_seal_certificate_verification_sha256":
            source_verification_hash,
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
        "archive_seal_certificate_evidence_package_sha256"
    ] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_seal_certificate_archive_seal_certificate_"
        "evidence_package_v75_2be.json": output,
        "registry_snapshot_seal_certificate_archive_seal_certificate_"
        "evidence_package_manifest_v75_2be.json": {
            "evidence_package_manifest": output["evidence_package_manifest"],
            "evidence_package_manifest_sha256": output[
                "evidence_package_manifest_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_certificate_"
        "evidence_component_hash_map_v75_2be.json": {
            "evidence_component_hash_map": output[
                "evidence_component_hash_map"
            ],
            "evidence_component_hash_map_sha256": output[
                "evidence_component_hash_map_sha256"
            ],
        },
        "packaged_verified_archive_seal_certificate_index_v75_2be.json": {
            "packaged_verified_receipt_count": output[
                "packaged_verified_receipt_count"
            ],
            "packaged_verified_archive_seal_certificate_index": output[
                "packaged_verified_archive_seal_certificate_index"
            ],
            "packaged_verified_archive_seal_certificate_index_sha256":
                output[
                    "packaged_verified_archive_seal_certificate_index_sha256"
                ],
        },
        "registry_snapshot_seal_certificate_archive_seal_certificate_"
        "evidence_package_checks_v75_2be.json": {
            "evidence_package_checks": output["evidence_package_checks"],
            "evidence_package_checks_sha256": output[
                "evidence_package_checks_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_certificate_"
        "evidence_package_ledger_v75_2be.json": {
            "evidence_package_ledger": output["evidence_package_ledger"],
            "evidence_package_ledger_sha256": output[
                "evidence_package_ledger_sha256"
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
        output = build_evidence_package(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
        )
        write_outputs(output, Path(args.output_dir))
        keys = (
            "status",
            "decision",
            (
                "certificate_registry_snapshot_seal_certificate_archive_"
                "seal_certificate_evidence_package_id"
            ),
            "evidence_package_state",
            "packaged_verified_receipt_count",
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
            "network_used",
            "approved_for_live",
            (
                "offline_paper_certificate_registry_snapshot_seal_"
                "certificate_archive_seal_certificate_"
                "evidence_package_sha256"
            ),
        )
        print(json.dumps(
            {key: output[key] for key in keys},
            indent=2,
            sort_keys=True,
        ))
        return 0
    except (
        EvidencePackageBuilderError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": (
                "offline_paper_certificate_registry_snapshot_seal_"
                "certificate_archive_seal_certificate_"
                "evidence_package_build_failed"
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
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
