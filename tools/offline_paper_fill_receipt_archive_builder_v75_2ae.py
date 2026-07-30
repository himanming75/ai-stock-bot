from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AE"
SCHEMA = "v75.2ae.offline_paper_fill_receipt_archive_package.1"
SOURCE_SCHEMA = "v75.2ad.offline_paper_fill_receipt_verification.1"
SOURCE_VERSION = "75.2AD"


class OfflinePaperFillReceiptArchiveError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflinePaperFillReceiptArchiveError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OfflinePaperFillReceiptArchiveError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OfflinePaperFillReceiptArchiveError("top-level JSON must be an object")
    return value


def parse_ts(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise OfflinePaperFillReceiptArchiveError("archived_at invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OfflinePaperFillReceiptArchiveError("archived_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise OfflinePaperFillReceiptArchiveError("archived_at must include timezone")
    return parsed.isoformat()


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("archive_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_ONLY":
        raise OfflinePaperFillReceiptArchiveError("archive_scope invalid")
    for key in (
        "require_receipt_verification_integrity",
        "require_verified_receipts_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_zero_settlement_and_account_mutations",
        "create_archive_manifest",
        "create_archive_index",
    ):
        if config.get(key) is not True:
            raise OfflinePaperFillReceiptArchiveError(f"{key} must be true")
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
            raise OfflinePaperFillReceiptArchiveError(f"{key} must be false")


def _require_hash(source: Dict[str, Any], field: str, hash_field: str) -> None:
    if source.get(hash_field) != sha256_of(source.get(field)):
        raise OfflinePaperFillReceiptArchiveError(f"{field} integrity failed")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise OfflinePaperFillReceiptArchiveError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("version") != SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveError("unsupported source schema or version")
    if source.get("decision") != "offline_paper_fill_receipts_verified":
        raise OfflinePaperFillReceiptArchiveError("source decision invalid")
    if source.get("verification_scope") != "OFFLINE_PAPER_FILL_RECEIPT_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveError("source verification scope invalid")
    if source.get("verification_state") != "VERIFIED_OFFLINE_FILL_RECEIPTS":
        raise OfflinePaperFillReceiptArchiveError("source verification state invalid")
    if source.get("receipts_verified") is not True:
        raise OfflinePaperFillReceiptArchiveError("receipt verification incomplete")

    observed = source.get("offline_paper_fill_receipt_verification_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_receipt_verification_sha256", None)
    if observed != sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveError("receipt verification integrity failed")

    for field, hash_field in (
        ("verified_receipts", "verified_receipts_sha256"),
        ("verification_checks", "verification_checks_sha256"),
        ("verification_ledger", "verification_ledger_sha256"),
    ):
        _require_hash(source, field, hash_field)

    receipts = source.get("verified_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise OfflinePaperFillReceiptArchiveError("verified receipts required")
    if source.get("verified_receipt_count") != len(receipts):
        raise OfflinePaperFillReceiptArchiveError("verified receipt count mismatch")

    receipt_verification_id = source.get("fill_receipt_verification_id")
    if not isinstance(receipt_verification_id, str) or not receipt_verification_id.startswith("FRV-"):
        raise OfflinePaperFillReceiptArchiveError("fill receipt verification id invalid")

    seen = set()
    for index, item in enumerate(receipts, start=1):
        if not isinstance(item, dict):
            raise OfflinePaperFillReceiptArchiveError("verified receipt must be an object")
        if item.get("receipt_index") != index:
            raise OfflinePaperFillReceiptArchiveError("verified receipt index mismatch")
        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-") or receipt_id in seen:
            raise OfflinePaperFillReceiptArchiveError("verified receipt id invalid or duplicate")
        seen.add(receipt_id)
        for key in (
            "receipt_sha256", "fill_id", "paper_order_id", "offline_submission_id",
            "symbol", "side",
        ):
            if not isinstance(item.get(key), str) or not item.get(key):
                raise OfflinePaperFillReceiptArchiveError(f"verified receipt {key} invalid")
        quantity, price = item.get("filled_quantity"), item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise OfflinePaperFillReceiptArchiveError("verified receipt quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise OfflinePaperFillReceiptArchiveError("verified receipt price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise OfflinePaperFillReceiptArchiveError("verified receipt notional invalid")
        if item.get("verification_state") != "VERIFIED_OFFLINE_FILL_RECEIPT_ONLY":
            raise OfflinePaperFillReceiptArchiveError("verified receipt state invalid")

    checks = source.get("verification_checks")
    ledger = source.get("verification_ledger")
    if not isinstance(checks, list) or len(checks) != 12:
        raise OfflinePaperFillReceiptArchiveError("verification checks invalid")
    if not isinstance(ledger, list) or len(ledger) != 6:
        raise OfflinePaperFillReceiptArchiveError("verification ledger invalid")
    for i, item in enumerate(checks, start=1):
        if item.get("check_index") != i or item.get("state") not in {"PASS", "LOCKED", "ENFORCED"}:
            raise OfflinePaperFillReceiptArchiveError("verification check sequence invalid")
    for i, item in enumerate(ledger, start=1):
        if item.get("ledger_index") != i or item.get("receipt_verification_id") != receipt_verification_id:
            raise OfflinePaperFillReceiptArchiveError("verification ledger sequence invalid")

    gate = source.get("verification_gate", {})
    expected_gate = {
        "receipts_verified": True,
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
            raise OfflinePaperFillReceiptArchiveError(f"verification_gate {key} invalid")

    for key in (
        "settlements_created", "positions_updated", "cash_updates_created",
        "portfolio_updates_created", "external_orders_submitted", "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise OfflinePaperFillReceiptArchiveError(f"mutation detected: {key}")
    for key in (
        "settlement_execution_allowed", "position_update_allowed", "cash_update_allowed",
        "portfolio_update_allowed", "external_order_submission_allowed", "broker_routing_allowed",
        "paper_broker_allowed", "live_orders_allowed", "network_allowed",
        "broker_connection_allowed", "approved_for_live", "network_used",
    ):
        if source.get(key) is not False:
            raise OfflinePaperFillReceiptArchiveError(f"unsafe source state: {key}")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise OfflinePaperFillReceiptArchiveError("safety lock invalid")
    return receipts


def build_archive(
    source: Dict[str, Any],
    config: Dict[str, Any],
    archived_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    verified_receipts = validate_source(source)
    when = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if archived_at is None else parse_ts(archived_at)
    )
    package_id = "FRA-" + hashlib.sha256(
        f"{source['fill_receipt_verification_id']}|"
        f"{source['offline_paper_fill_receipt_verification_sha256']}|"
        f"{when}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    archive_index = [{
        "archive_index": index,
        "receipt_id": item["receipt_id"],
        "receipt_sha256": item["receipt_sha256"],
        "fill_id": item["fill_id"],
        "symbol": item["symbol"],
        "side": item["side"],
        "filled_quantity": item["filled_quantity"],
        "fill_price": item["fill_price"],
        "notional_value": item["notional_value"],
        "archive_state": "INDEXED_VERIFIED_OFFLINE_RECEIPT",
    } for index, item in enumerate(verified_receipts, start=1)]

    manifest_entries = [
        {
            "entry_index": 1,
            "artifact": "SOURCE_RECEIPT_VERIFICATION",
            "artifact_id": source["fill_receipt_verification_id"],
            "artifact_sha256": source["offline_paper_fill_receipt_verification_sha256"],
            "state": "LOCKED",
        },
        {
            "entry_index": 2,
            "artifact": "VERIFIED_RECEIPT_COLLECTION",
            "artifact_id": source["receipt_batch_id"],
            "artifact_sha256": source["verified_receipts_sha256"],
            "state": "LOCKED",
        },
        {
            "entry_index": 3,
            "artifact": "SOURCE_VERIFICATION_CHECKS",
            "artifact_id": source["fill_receipt_verification_id"],
            "artifact_sha256": source["verification_checks_sha256"],
            "state": "LOCKED",
        },
        {
            "entry_index": 4,
            "artifact": "SOURCE_VERIFICATION_LEDGER",
            "artifact_id": source["fill_receipt_verification_id"],
            "artifact_sha256": source["verification_ledger_sha256"],
            "state": "LOCKED",
        },
    ]

    checks = [
        {"check_index": 1, "check": "SOURCE_VERIFICATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "VERIFIED_RECEIPT_COLLECTION_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "SOURCE_CHECKS_AND_LEDGER_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "ARCHIVE_PACKAGE_ID_DETERMINISTIC", "state": "PASS"},
        {"check_index": 5, "check": "ARCHIVE_INDEX_CREATED", "state": "PASS"},
        {"check_index": 6, "check": "ARCHIVE_MANIFEST_CREATED", "state": "PASS"},
        {"check_index": 7, "check": "RECEIPT_NOTIONALS_PRESERVED", "state": "PASS"},
        {"check_index": 8, "check": "ARCHIVE_CONTENT_IMMUTABLE", "state": "LOCKED"},
        {"check_index": 9, "check": "SETTLEMENT_AND_ACCOUNT_MUTATIONS_ABSENT", "state": "ENFORCED"},
        {"check_index": 10, "check": "BROKER_EXTERNAL_SUBMISSION_BLOCKED", "state": "PASS"},
        {"check_index": 11, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "RECEIPT_VERIFICATION_ACCEPTED", "state": "PASS", "archive_package_id": package_id},
        {"ledger_index": 2, "event": "VERIFIED_RECEIPTS_INDEXED", "state": "INDEXED", "archive_package_id": package_id},
        {"ledger_index": 3, "event": "ARCHIVE_MANIFEST_LOCKED", "state": "LOCKED", "archive_package_id": package_id},
        {"ledger_index": 4, "event": "ARCHIVE_PACKAGE_ASSEMBLED", "state": "CREATED", "archive_package_id": package_id},
        {"ledger_index": 5, "event": "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT", "state": "ENFORCED", "archive_package_id": package_id},
        {"ledger_index": 6, "event": "OFFLINE_RECEIPT_ARCHIVE_PACKAGE_COMPLETED", "state": "ARCHIVED", "archive_package_id": package_id},
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipt_archive_package_created",
        "fill_receipt_archive_package_id": package_id,
        "fill_receipt_verification_id": source["fill_receipt_verification_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "archive_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_ONLY",
        "archive_state": "ARCHIVED_VERIFIED_OFFLINE_RECEIPTS",
        "archived_at": when,
        "archived_receipt_count": len(archive_index),
        "archive_index": archive_index,
        "archive_index_sha256": sha256_of(archive_index),
        "archive_manifest": manifest_entries,
        "archive_manifest_sha256": sha256_of(manifest_entries),
        "archive_checks": checks,
        "archive_checks_sha256": sha256_of(checks),
        "archive_ledger": ledger,
        "archive_ledger_sha256": sha256_of(ledger),
        "archive_gate": {
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
            "next_version": "75.2AF",
        },
        "source_fill_receipt_verification_sha256": source["offline_paper_fill_receipt_verification_sha256"],
        "source_verified_receipts_sha256": source["verified_receipts_sha256"],
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
    output["offline_paper_fill_receipt_archive_package_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_receipt_archive_package_v75_2ae.json": output,
        "offline_paper_fill_receipt_archive_index_v75_2ae.json": {
            "fill_receipt_archive_package_id": output["fill_receipt_archive_package_id"],
            "archived_receipt_count": output["archived_receipt_count"],
            "archive_index": output["archive_index"],
            "archive_index_sha256": output["archive_index_sha256"],
        },
        "offline_paper_fill_receipt_archive_manifest_v75_2ae.json": {
            "fill_receipt_archive_package_id": output["fill_receipt_archive_package_id"],
            "archive_manifest": output["archive_manifest"],
            "archive_manifest_sha256": output["archive_manifest_sha256"],
        },
        "offline_paper_fill_receipt_archive_ledger_v75_2ae.json": {
            "fill_receipt_archive_package_id": output["fill_receipt_archive_package_id"],
            "archive_ledger": output["archive_ledger"],
            "archive_ledger_sha256": output["archive_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_receipt_archive_package_v75_2ae.sha256").write_text(
        output["offline_paper_fill_receipt_archive_package_sha256"] + "\n",
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
        print(json.dumps({
            "status": output["status"],
            "decision": output["decision"],
            "fill_receipt_archive_package_id": output["fill_receipt_archive_package_id"],
            "archive_state": output["archive_state"],
            "archived_receipt_count": output["archived_receipt_count"],
            "settlements_created": 0,
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_receipt_archive_package_sha256": output["offline_paper_fill_receipt_archive_package_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_receipt_archive_package_creation_failed",
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
