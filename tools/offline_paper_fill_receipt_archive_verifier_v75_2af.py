from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AF"
SCHEMA = "v75.2af.offline_paper_fill_receipt_archive_package_verification.1"
SOURCE_SCHEMA = "v75.2ae.offline_paper_fill_receipt_archive_package.1"
SOURCE_VERSION = "75.2AE"


class OfflinePaperFillReceiptArchiveVerificationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflinePaperFillReceiptArchiveVerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OfflinePaperFillReceiptArchiveVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OfflinePaperFillReceiptArchiveVerificationError("top-level JSON must be an object")
    return value


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("verification_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveVerificationError("verification_scope invalid")
    for key in (
        "require_archive_package_integrity",
        "require_archive_index_integrity",
        "require_archive_manifest_integrity",
        "require_archive_checks_integrity",
        "require_archive_ledger_integrity",
        "require_deterministic_archive_package_id",
        "require_receipt_notional_recalculation",
        "require_zero_settlement_and_account_mutations",
    ):
        if config.get(key) is not True:
            raise OfflinePaperFillReceiptArchiveVerificationError(f"{key} must be true")
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
            raise OfflinePaperFillReceiptArchiveVerificationError(f"{key} must be false")


def _require_hash(source: Dict[str, Any], field: str, hash_field: str) -> None:
    if source.get(hash_field) != sha256_of(source.get(field)):
        raise OfflinePaperFillReceiptArchiveVerificationError(f"{field} integrity failed")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise OfflinePaperFillReceiptArchiveVerificationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("version") != SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveVerificationError("unsupported source schema or version")
    if source.get("decision") != "offline_paper_fill_receipt_archive_package_created":
        raise OfflinePaperFillReceiptArchiveVerificationError("source decision invalid")
    if source.get("archive_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_ONLY":
        raise OfflinePaperFillReceiptArchiveVerificationError("source archive scope invalid")
    if source.get("archive_state") != "ARCHIVED_VERIFIED_OFFLINE_RECEIPTS":
        raise OfflinePaperFillReceiptArchiveVerificationError("source archive state invalid")

    observed = source.get("offline_paper_fill_receipt_archive_package_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_receipt_archive_package_sha256", None)
    if observed != sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveVerificationError("archive package integrity failed")

    for field, hash_field in (
        ("archive_index", "archive_index_sha256"),
        ("archive_manifest", "archive_manifest_sha256"),
        ("archive_checks", "archive_checks_sha256"),
        ("archive_ledger", "archive_ledger_sha256"),
    ):
        _require_hash(source, field, hash_field)

    package_id = source.get("fill_receipt_archive_package_id")
    receipt_verification_id = source.get("fill_receipt_verification_id")
    if not isinstance(package_id, str) or not package_id.startswith("FRA-"):
        raise OfflinePaperFillReceiptArchiveVerificationError("archive package id invalid")
    if not isinstance(receipt_verification_id, str) or not receipt_verification_id.startswith("FRV-"):
        raise OfflinePaperFillReceiptArchiveVerificationError("receipt verification id invalid")

    expected_package_id = "FRA-" + hashlib.sha256(
        f"{receipt_verification_id}|{source.get('source_fill_receipt_verification_sha256')}|"
        f"{source.get('archived_at')}|{SOURCE_VERSION}".encode()
    ).hexdigest()[:16].upper()
    if package_id != expected_package_id:
        raise OfflinePaperFillReceiptArchiveVerificationError("deterministic archive package id mismatch")

    index = source.get("archive_index")
    if not isinstance(index, list) or not index:
        raise OfflinePaperFillReceiptArchiveVerificationError("archive index required")
    if source.get("archived_receipt_count") != len(index):
        raise OfflinePaperFillReceiptArchiveVerificationError("archive receipt count mismatch")

    seen_receipts = set()
    for i, item in enumerate(index, start=1):
        if not isinstance(item, dict):
            raise OfflinePaperFillReceiptArchiveVerificationError("archive index entry must be an object")
        if item.get("archive_index") != i:
            raise OfflinePaperFillReceiptArchiveVerificationError("archive index sequence invalid")
        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-") or receipt_id in seen_receipts:
            raise OfflinePaperFillReceiptArchiveVerificationError("archive receipt id invalid or duplicate")
        seen_receipts.add(receipt_id)
        for key in ("receipt_sha256", "fill_id", "symbol", "side"):
            if not isinstance(item.get(key), str) or not item.get(key):
                raise OfflinePaperFillReceiptArchiveVerificationError(f"archive index {key} invalid")
        quantity = item.get("filled_quantity")
        price = item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise OfflinePaperFillReceiptArchiveVerificationError("archive quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise OfflinePaperFillReceiptArchiveVerificationError("archive price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise OfflinePaperFillReceiptArchiveVerificationError("archive notional mismatch")
        if item.get("archive_state") != "INDEXED_VERIFIED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveVerificationError("archive index state invalid")

    manifest = source.get("archive_manifest")
    if not isinstance(manifest, list) or len(manifest) != 4:
        raise OfflinePaperFillReceiptArchiveVerificationError("archive manifest invalid")
    expected_artifacts = (
        "SOURCE_RECEIPT_VERIFICATION",
        "VERIFIED_RECEIPT_COLLECTION",
        "SOURCE_VERIFICATION_CHECKS",
        "SOURCE_VERIFICATION_LEDGER",
    )
    expected_hashes = (
        source.get("source_fill_receipt_verification_sha256"),
        source.get("source_verified_receipts_sha256"),
        source.get("source_verification_checks_sha256"),
        source.get("source_verification_ledger_sha256"),
    )
    for i, (entry, artifact, artifact_hash) in enumerate(zip(manifest, expected_artifacts, expected_hashes), start=1):
        if entry.get("entry_index") != i or entry.get("artifact") != artifact:
            raise OfflinePaperFillReceiptArchiveVerificationError("archive manifest sequence invalid")
        if entry.get("artifact_sha256") != artifact_hash or entry.get("state") != "LOCKED":
            raise OfflinePaperFillReceiptArchiveVerificationError("archive manifest linkage invalid")

    checks = source.get("archive_checks")
    ledger = source.get("archive_ledger")
    if not isinstance(checks, list) or len(checks) != 12:
        raise OfflinePaperFillReceiptArchiveVerificationError("archive checks invalid")
    if not isinstance(ledger, list) or len(ledger) != 6:
        raise OfflinePaperFillReceiptArchiveVerificationError("archive ledger invalid")
    for i, item in enumerate(checks, start=1):
        if item.get("check_index") != i or item.get("state") not in {"PASS", "LOCKED", "ENFORCED"}:
            raise OfflinePaperFillReceiptArchiveVerificationError("archive check sequence invalid")
    for i, item in enumerate(ledger, start=1):
        if item.get("ledger_index") != i or item.get("archive_package_id") != package_id:
            raise OfflinePaperFillReceiptArchiveVerificationError("archive ledger sequence invalid")

    gate = source.get("archive_gate", {})
    expected_gate = {
        "archive_package_created": True,
        "archive_package_immutable": True,
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
            raise OfflinePaperFillReceiptArchiveVerificationError(f"archive_gate {key} invalid")

    for key in (
        "settlements_created", "positions_updated", "cash_updates_created",
        "portfolio_updates_created", "external_orders_submitted", "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise OfflinePaperFillReceiptArchiveVerificationError(f"mutation detected: {key}")
    for key in (
        "settlement_execution_allowed", "position_update_allowed", "cash_update_allowed",
        "portfolio_update_allowed", "external_order_submission_allowed", "broker_routing_allowed",
        "paper_broker_allowed", "live_orders_allowed", "network_allowed",
        "broker_connection_allowed", "approved_for_live", "network_used",
    ):
        if source.get(key) is not False:
            raise OfflinePaperFillReceiptArchiveVerificationError(f"unsafe source state: {key}")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise OfflinePaperFillReceiptArchiveVerificationError("safety lock invalid")
    return index


def build_verification(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    validate_config(config)
    archive_index = validate_source(source)
    verification_id = "FAV-" + hashlib.sha256(
        f"{source['fill_receipt_archive_package_id']}|"
        f"{source['offline_paper_fill_receipt_archive_package_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    verified_index = [{
        "archive_index": item["archive_index"],
        "receipt_id": item["receipt_id"],
        "receipt_sha256": item["receipt_sha256"],
        "fill_id": item["fill_id"],
        "symbol": item["symbol"],
        "side": item["side"],
        "filled_quantity": item["filled_quantity"],
        "fill_price": item["fill_price"],
        "notional_value": item["notional_value"],
        "verification_state": "VERIFIED_ARCHIVED_OFFLINE_RECEIPT",
    } for item in archive_index]

    checks = [
        {"check_index": 1, "check": "ARCHIVE_PACKAGE_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "ARCHIVE_INDEX_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "ARCHIVE_MANIFEST_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "ARCHIVE_CHECKS_INTEGRITY", "state": "PASS"},
        {"check_index": 5, "check": "ARCHIVE_LEDGER_INTEGRITY", "state": "PASS"},
        {"check_index": 6, "check": "ARCHIVE_PACKAGE_ID_DETERMINISTIC", "state": "PASS"},
        {"check_index": 7, "check": "ARCHIVED_RECEIPT_LINKAGES_VERIFIED", "state": "PASS"},
        {"check_index": 8, "check": "ARCHIVED_RECEIPT_NOTIONALS_RECALCULATED", "state": "PASS"},
        {"check_index": 9, "check": "ARCHIVE_IMMUTABILITY_CONFIRMED", "state": "LOCKED"},
        {"check_index": 10, "check": "SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT", "state": "ENFORCED"},
        {"check_index": 11, "check": "NETWORK_AND_BROKER_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "ARCHIVE_PACKAGE_HASH_VERIFIED", "state": "PASS", "archive_verification_id": verification_id},
        {"ledger_index": 2, "event": "ARCHIVE_INDEX_VERIFIED", "state": "VERIFIED", "archive_verification_id": verification_id},
        {"ledger_index": 3, "event": "ARCHIVE_MANIFEST_VERIFIED", "state": "VERIFIED", "archive_verification_id": verification_id},
        {"ledger_index": 4, "event": "ARCHIVE_CHECKS_AND_LEDGER_VERIFIED", "state": "PASS", "archive_verification_id": verification_id},
        {"ledger_index": 5, "event": "ARCHIVE_IMMUTABILITY_AND_SAFETY_CONFIRMED", "state": "ENFORCED", "archive_verification_id": verification_id},
        {"ledger_index": 6, "event": "OFFLINE_RECEIPT_ARCHIVE_VERIFICATION_COMPLETED", "state": "VERIFIED", "archive_verification_id": verification_id},
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipt_archive_package_verified",
        "fill_receipt_archive_verification_id": verification_id,
        "fill_receipt_archive_package_id": source["fill_receipt_archive_package_id"],
        "fill_receipt_verification_id": source["fill_receipt_verification_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "verification_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_VERIFICATION_ONLY",
        "verification_state": "VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_PACKAGE",
        "archive_package_verified": True,
        "verified_archived_receipt_count": len(verified_index),
        "verified_archive_index": verified_index,
        "verified_archive_index_sha256": sha256_of(verified_index),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "archive_package_verified": True,
            "archive_package_immutable": True,
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AG",
        },
        "source_archive_package_sha256": source["offline_paper_fill_receipt_archive_package_sha256"],
        "source_archive_index_sha256": source["archive_index_sha256"],
        "source_archive_manifest_sha256": source["archive_manifest_sha256"],
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
    output["offline_paper_fill_receipt_archive_verification_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_receipt_archive_verification_v75_2af.json": output,
        "offline_paper_verified_fill_receipt_archive_index_v75_2af.json": {
            "fill_receipt_archive_verification_id": output["fill_receipt_archive_verification_id"],
            "verified_archived_receipt_count": output["verified_archived_receipt_count"],
            "verified_archive_index": output["verified_archive_index"],
            "verified_archive_index_sha256": output["verified_archive_index_sha256"],
        },
        "offline_paper_fill_receipt_archive_verification_checks_v75_2af.json": {
            "fill_receipt_archive_verification_id": output["fill_receipt_archive_verification_id"],
            "verification_checks": output["verification_checks"],
            "verification_checks_sha256": output["verification_checks_sha256"],
        },
        "offline_paper_fill_receipt_archive_verification_ledger_v75_2af.json": {
            "fill_receipt_archive_verification_id": output["fill_receipt_archive_verification_id"],
            "verification_ledger": output["verification_ledger"],
            "verification_ledger_sha256": output["verification_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_receipt_archive_verification_v75_2af.sha256").write_text(
        output["offline_paper_fill_receipt_archive_verification_sha256"] + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        output = build_verification(read_json(Path(args.input)), read_json(Path(args.config)))
        write_outputs(output, Path(args.output_dir))
        print(json.dumps({
            "status": output["status"],
            "decision": output["decision"],
            "fill_receipt_archive_verification_id": output["fill_receipt_archive_verification_id"],
            "verification_state": output["verification_state"],
            "verified_archived_receipt_count": output["verified_archived_receipt_count"],
            "settlements_created": 0,
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_receipt_archive_verification_sha256": output["offline_paper_fill_receipt_archive_verification_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveVerificationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_receipt_archive_package_verification_failed",
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
