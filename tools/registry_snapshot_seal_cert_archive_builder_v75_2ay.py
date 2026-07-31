from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AY"
SCHEMA = "v75.2ay.offline_paper_certificate_registry_snapshot_seal_certificate_archive.1"
SOURCE_VERSION = "75.2AX"
SOURCE_SCHEMA = "v75.2ax.offline_paper_certificate_registry_snapshot_seal_certificate_verification.1"


class RegistrySnapshotSealCertificateArchiveError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistrySnapshotSealCertificateArchiveError(
            f"file not found: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RegistrySnapshotSealCertificateArchiveError(
            f"invalid JSON: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise RegistrySnapshotSealCertificateArchiveError(
            "top-level JSON must be an object"
        )
    return data


def parse_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise RegistrySnapshotSealCertificateArchiveError("archived_at invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RegistrySnapshotSealCertificateArchiveError(
            "archived_at must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        raise RegistrySnapshotSealCertificateArchiveError(
            "archived_at must include timezone"
        )
    return parsed.isoformat()


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("archive_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_ONLY"
    ):
        raise RegistrySnapshotSealCertificateArchiveError(
            "archive_scope invalid"
        )

    required_true = (
        "require_certificate_verification_integrity",
        "require_verified_certified_sealed_snapshot_index_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_zero_settlement_and_account_mutations",
        "create_archive_manifest",
        "create_archived_certified_sealed_snapshot_index",
        "create_archive_checks",
        "create_archive_ledger",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise RegistrySnapshotSealCertificateArchiveError(
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
            raise RegistrySnapshotSealCertificateArchiveError(
                f"{key} must be false"
            )


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise RegistrySnapshotSealCertificateArchiveError(
            "source status must be PASS"
        )
    if source.get("version") != SOURCE_VERSION:
        raise RegistrySnapshotSealCertificateArchiveError(
            "unsupported source version"
        )
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise RegistrySnapshotSealCertificateArchiveError(
            "unsupported source schema"
        )
    if source.get("decision") != (
        "offline_paper_certificate_registry_snapshot_seal_certificate_verified"
    ):
        raise RegistrySnapshotSealCertificateArchiveError(
            "source decision invalid"
        )
    if source.get("verification_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "VERIFICATION_ONLY"
    ):
        raise RegistrySnapshotSealCertificateArchiveError(
            "source verification scope invalid"
        )
    if source.get("verification_state") != (
        "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE"
    ):
        raise RegistrySnapshotSealCertificateArchiveError(
            "source verification state invalid"
        )
    if source.get("certificate_verified") is not True:
        raise RegistrySnapshotSealCertificateArchiveError(
            "certificate verification incomplete"
        )

    observed = source.get(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "verification_sha256"
    )
    clone = copy.deepcopy(source)
    clone.pop(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "verification_sha256",
        None,
    )
    if observed != sha256_of(clone):
        raise RegistrySnapshotSealCertificateArchiveError(
            "certificate verification integrity failed"
        )

    for field, hash_field in (
        (
            "verified_certified_sealed_snapshot_index",
            "verified_certified_sealed_snapshot_index_sha256",
        ),
        ("verification_checks", "verification_checks_sha256"),
        ("verification_ledger", "verification_ledger_sha256"),
    ):
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise RegistrySnapshotSealCertificateArchiveError(
                f"{field} integrity failed"
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
            raise RegistrySnapshotSealCertificateArchiveError(
                f"{label} invalid"
            )

    index = source.get("verified_certified_sealed_snapshot_index")
    if not isinstance(index, list) or not index:
        raise RegistrySnapshotSealCertificateArchiveError(
            "verified certified sealed snapshot index required"
        )
    if source.get("verified_certified_receipt_count") != len(index):
        raise RegistrySnapshotSealCertificateArchiveError(
            "verified certified receipt count mismatch"
        )

    seen_receipts = set()
    for i, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise RegistrySnapshotSealCertificateArchiveError(
                "verified certified index item invalid"
            )
        if item.get("verification_record_index") != i:
            raise RegistrySnapshotSealCertificateArchiveError(
                "verified certified index sequence invalid"
            )

        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-"):
            raise RegistrySnapshotSealCertificateArchiveError(
                "receipt id invalid"
            )
        if receipt_id in seen_receipts:
            raise RegistrySnapshotSealCertificateArchiveError(
                "duplicate receipt id"
            )
        seen_receipts.add(receipt_id)

        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise RegistrySnapshotSealCertificateArchiveError(
                "filled quantity invalid"
            )
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise RegistrySnapshotSealCertificateArchiveError(
                "fill price invalid"
            )
        if float(price) <= 0:
            raise RegistrySnapshotSealCertificateArchiveError(
                "fill price invalid"
            )
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise RegistrySnapshotSealCertificateArchiveError(
                "notional value invalid"
            )
        if item.get("verification_state") != (
            "VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_ARCHIVED_"
            "OFFLINE_RECEIPT"
        ):
            raise RegistrySnapshotSealCertificateArchiveError(
                "verified certified receipt state invalid"
            )

    if len(source.get("verification_checks", [])) != 12:
        raise RegistrySnapshotSealCertificateArchiveError(
            "verification checks invalid"
        )
    if len(source.get("verification_ledger", [])) != 6:
        raise RegistrySnapshotSealCertificateArchiveError(
            "verification ledger invalid"
        )

    gate = source.get("verification_gate", {})
    expected_gate = {
        "certificate_registry_snapshot_seal_certificate_verified": True,
        "certificate_immutable": True,
        "verification_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_VERIFICATION_ONLY"
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
            raise RegistrySnapshotSealCertificateArchiveError(
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
            raise RegistrySnapshotSealCertificateArchiveError(
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
            raise RegistrySnapshotSealCertificateArchiveError(
                f"unsafe source state: {key}"
            )

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise RegistrySnapshotSealCertificateArchiveError(
            "safety lock invalid"
        )

    return index


def build_archive(
    source: Dict[str, Any],
    config: Dict[str, Any],
    archived_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    when = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if archived_at is None
        else parse_timestamp(archived_at)
    )

    archive_seed = (
        f"{source['certificate_registry_snapshot_seal_certificate_verification_id']}|"
        f"{source['offline_paper_certificate_registry_snapshot_seal_certificate_verification_sha256']}|"
        f"{when}|{VERSION}"
    )
    archive_id = "CRSCA-" + hashlib.sha256(
        archive_seed.encode("utf-8")
    ).hexdigest()[:16].upper()

    manifest = {
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
        "archived_receipt_count": len(index),
        "archive_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_ONLY"
        ),
        "archive_state": (
            "ARCHIVED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE"
        ),
        "archived_at": when,
    }

    archived_index = [
        {
            "archive_record_index": i,
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
            "archive_state": (
                "ARCHIVED_VERIFIED_CERTIFIED_SEALED_SNAPSHOTTED_REGISTERED_"
                "OFFLINE_RECEIPT"
            ),
        }
        for i, item in enumerate(index, 1)
    ]

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate(
            (
                ("CERTIFICATE_VERIFICATION_INTEGRITY", "PASS"),
                ("VERIFIED_CERTIFIED_SEALED_INDEX_INTEGRITY", "PASS"),
                ("VERIFICATION_CHECKS_INTEGRITY", "PASS"),
                ("VERIFICATION_LEDGER_INTEGRITY", "PASS"),
                ("ARCHIVE_ID_DETERMINISTIC", "PASS"),
                ("ARCHIVE_MANIFEST_CREATED", "PASS"),
                ("ARCHIVED_CERTIFIED_SEALED_INDEX_CREATED", "PASS"),
                ("RECEIPT_LINKAGES_AND_NOTIONALS_PRESERVED", "PASS"),
                ("ARCHIVE_CONTENT_IMMUTABLE", "LOCKED"),
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
            "archive_id": archive_id,
        }
        for i, (event, state) in enumerate(
            (
                ("SNAPSHOT_SEAL_CERTIFICATE_VERIFICATION_ACCEPTED", "PASS"),
                ("ARCHIVE_MANIFEST_CREATED", "CREATED"),
                ("VERIFIED_CERTIFIED_SEALED_INDEX_ARCHIVED", "ARCHIVED"),
                ("ARCHIVE_CONTENT_LOCKED", "LOCKED"),
                (
                    "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT",
                    "ENFORCED",
                ),
                (
                    "OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
                    "ARCHIVE_COMPLETED",
                    "ARCHIVED",
                ),
            ),
            1,
        )
    ]

    output = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_archived"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_id": archive_id,
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
        "archive_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_ONLY"
        ),
        "archive_state": (
            "ARCHIVED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE"
        ),
        "archived_at": when,
        "archive_manifest": manifest,
        "archive_manifest_sha256": sha256_of(manifest),
        "archived_receipt_count": len(archived_index),
        "archived_certified_sealed_snapshot_index": archived_index,
        "archived_certified_sealed_snapshot_index_sha256": sha256_of(
            archived_index
        ),
        "archive_checks": checks,
        "archive_checks_sha256": sha256_of(checks),
        "archive_ledger": ledger,
        "archive_ledger_sha256": sha256_of(ledger),
        "archive_gate": {
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
            "next_version": "75.2AZ",
        },
        "source_certificate_verification_sha256": source[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "verification_sha256"
        ],
        "source_verified_certified_sealed_snapshot_index_sha256": source[
            "verified_certified_sealed_snapshot_index_sha256"
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
        "offline_paper_certificate_registry_snapshot_seal_certificate_archive_sha256"
    ] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "registry_snapshot_seal_certificate_archive_v75_2ay.json": output,
        "registry_snapshot_seal_certificate_archive_manifest_v75_2ay.json": {
            "archive_id": output[
                "certificate_registry_snapshot_seal_certificate_archive_id"
            ],
            "archive_manifest": output["archive_manifest"],
            "archive_manifest_sha256": output["archive_manifest_sha256"],
        },
        "archived_certified_sealed_snapshot_index_v75_2ay.json": {
            "archive_id": output[
                "certificate_registry_snapshot_seal_certificate_archive_id"
            ],
            "archived_receipt_count": output["archived_receipt_count"],
            "archived_certified_sealed_snapshot_index": output[
                "archived_certified_sealed_snapshot_index"
            ],
            "archived_certified_sealed_snapshot_index_sha256": output[
                "archived_certified_sealed_snapshot_index_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_ledger_v75_2ay.json": {
            "archive_id": output[
                "certificate_registry_snapshot_seal_certificate_archive_id"
            ],
            "archive_ledger": output["archive_ledger"],
            "archive_ledger_sha256": output["archive_ledger_sha256"],
        },
    }

    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (
        output_dir / "registry_snapshot_seal_certificate_archive_v75_2ay.sha256"
    ).write_text(
        output[
            "offline_paper_certificate_registry_snapshot_seal_certificate_archive_sha256"
        ]
        + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--archived-at")
    args = parser.parse_args(argv)

    try:
        output = build_archive(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.archived_at,
        )
        write_outputs(output, Path(args.output_dir))

        keys = (
            "status",
            "decision",
            "certificate_registry_snapshot_seal_certificate_archive_id",
            "archive_state",
            "archived_receipt_count",
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
            "network_used",
            "approved_for_live",
            "offline_paper_certificate_registry_snapshot_seal_certificate_archive_sha256",
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
        RegistrySnapshotSealCertificateArchiveError,
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
                        "certificate_archive_failed"
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
