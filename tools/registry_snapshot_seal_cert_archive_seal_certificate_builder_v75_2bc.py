from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2BC"
SCHEMA = (
    "v75.2bc.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal_certificate.1"
)
SOURCE_VERSION = "75.2BB"
SOURCE_SCHEMA = (
    "v75.2bb.offline_paper_certificate_registry_snapshot_seal_certificate_"
    "archive_seal_verification.1"
)


class ArchiveSealCertificateBuilderError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArchiveSealCertificateBuilderError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ArchiveSealCertificateBuilderError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ArchiveSealCertificateBuilderError("top-level JSON must be an object")
    return value


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("certificate_scope") != (
        "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL_CERTIFICATE_ONLY"
    ):
        raise ArchiveSealCertificateBuilderError("certificate_scope invalid")

    for key in (
        "require_archive_seal_verification_integrity",
        "require_deterministic_archive_seal_certificate_id",
        "require_receipt_linkage_and_notional_preservation",
        "require_zero_settlement_and_account_mutations",
        "create_archive_seal_certificate_manifest",
        "create_certified_verified_sealed_archived_snapshot_index",
        "create_archive_seal_certificate_checks",
        "create_archive_seal_certificate_ledger",
    ):
        if config.get(key) is not True:
            raise ArchiveSealCertificateBuilderError(f"{key} must be true")

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
            raise ArchiveSealCertificateBuilderError(f"{key} must be false")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise ArchiveSealCertificateBuilderError("source status must be PASS")
    if source.get("version") != SOURCE_VERSION:
        raise ArchiveSealCertificateBuilderError("unsupported source version")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise ArchiveSealCertificateBuilderError("unsupported source schema")
    if source.get("decision") != (
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_verified"
    ):
        raise ArchiveSealCertificateBuilderError("source decision invalid")
    if source.get("verification_state") != (
        "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
        "ARCHIVE_SEAL"
    ):
        raise ArchiveSealCertificateBuilderError("verification state invalid")

    observed = source.get(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_verification_sha256"
    )
    clone = copy.deepcopy(source)
    clone.pop(
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_verification_sha256",
        None,
    )
    if observed != sha256_of(clone):
        raise ArchiveSealCertificateBuilderError(
            "archive seal verification integrity failed"
        )

    index = source.get("verified_sealed_archived_certified_snapshot_index")
    if not isinstance(index, list) or not index:
        raise ArchiveSealCertificateBuilderError(
            "verified sealed archived certified snapshot index required"
        )
    if source.get("verified_sealed_archived_receipt_count") != len(index):
        raise ArchiveSealCertificateBuilderError("receipt count mismatch")
    if source.get(
        "verified_sealed_archived_certified_snapshot_index_sha256"
    ) != sha256_of(index):
        raise ArchiveSealCertificateBuilderError("verified index integrity failed")

    if source.get("archive_seal_verification_checks_sha256") != sha256_of(
        source.get("archive_seal_verification_checks")
    ):
        raise ArchiveSealCertificateBuilderError("verification checks integrity failed")
    if source.get("archive_seal_verification_ledger_sha256") != sha256_of(
        source.get("archive_seal_verification_ledger")
    ):
        raise ArchiveSealCertificateBuilderError("verification ledger integrity failed")

    for i, item in enumerate(index, 1):
        if item.get("archive_seal_verification_record_index") != i:
            raise ArchiveSealCertificateBuilderError("verified index sequence invalid")
        qty = item.get("filled_quantity")
        price = item.get("fill_price")
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ArchiveSealCertificateBuilderError("filled quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
            raise ArchiveSealCertificateBuilderError("fill price invalid")
        if item.get("notional_value") != round(float(price) * qty, 10):
            raise ArchiveSealCertificateBuilderError("notional value invalid")

    for key in (
        "settlements_created",
        "positions_updated",
        "cash_updates_created",
        "portfolio_updates_created",
        "external_orders_submitted",
        "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise ArchiveSealCertificateBuilderError(f"mutation detected: {key}")

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
            raise ArchiveSealCertificateBuilderError(f"unsafe source state: {key}")

    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise ArchiveSealCertificateBuilderError("safety lock invalid")

    return index


def build_archive_seal_certificate(
    source: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    validate_config(config)
    index = validate_source(source)

    verification_id = source[
        "certificate_registry_snapshot_seal_certificate_archive_seal_verification_id"
    ]
    source_hash = source[
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_verification_sha256"
    ]
    cert_id = "CRSCASC-" + hashlib.sha256(
        f"{verification_id}|{source_hash}|{VERSION}".encode("utf-8")
    ).hexdigest()[:16].upper()

    certified_index = []
    for i, item in enumerate(index, 1):
        certified_index.append({
            "archive_seal_certificate_record_index": i,
            **copy.deepcopy(item),
            "archive_seal_certificate_state": (
                "CERTIFIED_VERIFIED_SEALED_ARCHIVED_CERTIFIED_SEALED_"
                "SNAPSHOTTED_REGISTERED_OFFLINE_RECEIPT"
            ),
        })

    manifest = {
        "archive_seal_certificate_id": cert_id,
        "archive_seal_verification_id": verification_id,
        "archive_seal_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_seal_id"
        ],
        "archive_verification_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_verification_id"
        ],
        "archive_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_id"
        ],
        "receipt_batch_id": source["receipt_batch_id"],
        "certified_archived_receipt_count": len(certified_index),
        "certificate_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL_CERTIFICATE_ONLY"
        ),
        "certificate_state": (
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL"
        ),
    }

    checks = [
        {"check_index": i, "check": name, "state": state}
        for i, (name, state) in enumerate((
            ("ARCHIVE_SEAL_VERIFICATION_INTEGRITY", "PASS"),
            ("ARCHIVE_SEAL_CERTIFICATE_ID_DETERMINISTIC", "PASS"),
            ("CERTIFICATE_MANIFEST_CREATED", "PASS"),
            ("CERTIFIED_INDEX_CREATED", "PASS"),
            ("RECEIPT_LINKAGE_PRESERVED", "PASS"),
            ("NOTIONAL_VALUES_PRESERVED", "PASS"),
            ("SOURCE_VERIFICATION_IMMUTABLE", "LOCKED"),
            ("SETTLEMENT_MUTATIONS_ABSENT", "ENFORCED"),
            ("ACCOUNT_MUTATIONS_ABSENT", "ENFORCED"),
            ("BROKER_ROUTING_DISABLED", "PASS"),
            ("NETWORK_DISABLED", "PASS"),
            ("LIVE_TRADING_PROHIBITED", "ENFORCED"),
        ), 1)
    ]

    ledger = [
        {
            "ledger_index": i,
            "event": event,
            "state": state,
            "archive_seal_certificate_id": cert_id,
        }
        for i, (event, state) in enumerate((
            ("ARCHIVE_SEAL_VERIFICATION_ACCEPTED", "PASS"),
            ("ARCHIVE_SEAL_CERTIFICATE_MANIFEST_CREATED", "CREATED"),
            ("CERTIFIED_VERIFIED_SEALED_ARCHIVED_INDEX_CREATED", "CREATED"),
            ("ARCHIVE_SEAL_CERTIFICATE_EVIDENCE_LOCKED", "LOCKED"),
            ("ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT", "ENFORCED"),
            ("ARCHIVE_SEAL_CERTIFICATE_COMPLETED", "CERTIFIED"),
        ), 1)
    ]

    output = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_built"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_seal_certificate_id": cert_id,
        "certificate_registry_snapshot_seal_certificate_archive_seal_verification_id": verification_id,
        "certificate_registry_snapshot_seal_certificate_archive_seal_id": source[
            "certificate_registry_snapshot_seal_certificate_archive_seal_id"
        ],
        "receipt_batch_id": source["receipt_batch_id"],
        "certificate_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_ONLY"
        ),
        "archive_seal_certificate_state": (
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL"
        ),
        "archive_seal_certificate_manifest": manifest,
        "archive_seal_certificate_manifest_sha256": sha256_of(manifest),
        "certified_archived_receipt_count": len(certified_index),
        "certified_verified_sealed_archived_snapshot_index": certified_index,
        "certified_verified_sealed_archived_snapshot_index_sha256": sha256_of(
            certified_index
        ),
        "archive_seal_certificate_checks": checks,
        "archive_seal_certificate_checks_sha256": sha256_of(checks),
        "archive_seal_certificate_ledger": ledger,
        "archive_seal_certificate_ledger_sha256": sha256_of(ledger),
        "certificate_gate": {
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
            "next_version": "75.2BD",
        },
        "source_archive_seal_verification_sha256": source_hash,
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
        "archive_seal_certificate_sha256"
    ] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "registry_snapshot_seal_certificate_archive_seal_certificate_v75_2bc.json": output,
        "registry_snapshot_seal_certificate_archive_seal_certificate_manifest_v75_2bc.json": {
            "archive_seal_certificate_manifest": output[
                "archive_seal_certificate_manifest"
            ],
            "archive_seal_certificate_manifest_sha256": output[
                "archive_seal_certificate_manifest_sha256"
            ],
        },
        "certified_verified_sealed_archived_snapshot_index_v75_2bc.json": {
            "certified_archived_receipt_count": output[
                "certified_archived_receipt_count"
            ],
            "certified_verified_sealed_archived_snapshot_index": output[
                "certified_verified_sealed_archived_snapshot_index"
            ],
            "certified_verified_sealed_archived_snapshot_index_sha256": output[
                "certified_verified_sealed_archived_snapshot_index_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_certificate_checks_v75_2bc.json": {
            "archive_seal_certificate_checks": output[
                "archive_seal_certificate_checks"
            ],
            "archive_seal_certificate_checks_sha256": output[
                "archive_seal_certificate_checks_sha256"
            ],
        },
        "registry_snapshot_seal_certificate_archive_seal_certificate_ledger_v75_2bc.json": {
            "archive_seal_certificate_ledger": output[
                "archive_seal_certificate_ledger"
            ],
            "archive_seal_certificate_ledger_sha256": output[
                "archive_seal_certificate_ledger_sha256"
            ],
        },
    }
    for name, value in files.items():
        (output_dir / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        output = build_archive_seal_certificate(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
        )
        write_outputs(output, Path(args.output_dir))
        print(json.dumps({
            "status": output["status"],
            "decision": output["decision"],
            "certificate_registry_snapshot_seal_certificate_archive_seal_certificate_id":
                output["certificate_registry_snapshot_seal_certificate_archive_seal_certificate_id"],
            "archive_seal_certificate_state": output["archive_seal_certificate_state"],
            "certified_archived_receipt_count": output["certified_archived_receipt_count"],
            "settlements_created": output["settlements_created"],
            "positions_updated": output["positions_updated"],
            "cash_updates_created": output["cash_updates_created"],
            "portfolio_updates_created": output["portfolio_updates_created"],
            "external_orders_submitted": output["external_orders_submitted"],
            "broker_routes_created": output["broker_routes_created"],
            "network_used": output["network_used"],
            "approved_for_live": output["approved_for_live"],
            "offline_paper_certificate_registry_snapshot_seal_certificate_archive_seal_certificate_sha256":
                output["offline_paper_certificate_registry_snapshot_seal_certificate_archive_seal_certificate_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (ArchiveSealCertificateBuilderError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": (
                "offline_paper_certificate_registry_snapshot_seal_certificate_"
                "archive_seal_certificate_build_failed"
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
