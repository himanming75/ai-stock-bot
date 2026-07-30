from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AG"
SCHEMA = "v75.2ag.offline_paper_fill_receipt_archive_certificate.1"
SOURCE_SCHEMA = "v75.2af.offline_paper_fill_receipt_archive_package_verification.1"
SOURCE_VERSION = "75.2AF"


class OfflinePaperFillReceiptArchiveCertificateError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflinePaperFillReceiptArchiveCertificateError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OfflinePaperFillReceiptArchiveCertificateError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OfflinePaperFillReceiptArchiveCertificateError("top-level JSON must be an object")
    return value


def parse_ts(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise OfflinePaperFillReceiptArchiveCertificateError("certified_at invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OfflinePaperFillReceiptArchiveCertificateError("certified_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise OfflinePaperFillReceiptArchiveCertificateError("certified_at must include timezone")
    return parsed.isoformat()


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("certificate_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateError("certificate_scope invalid")
    for key in (
        "require_archive_verification_integrity",
        "require_verified_archive_index_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_zero_settlement_and_account_mutations",
        "create_certificate_summary",
        "create_certificate_checks",
        "create_certificate_ledger",
    ):
        if config.get(key) is not True:
            raise OfflinePaperFillReceiptArchiveCertificateError(f"{key} must be true")
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
            raise OfflinePaperFillReceiptArchiveCertificateError(f"{key} must be false")


def _require_hash(source: Dict[str, Any], field: str, hash_field: str) -> None:
    if source.get(hash_field) != sha256_of(source.get(field)):
        raise OfflinePaperFillReceiptArchiveCertificateError(f"{field} integrity failed")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise OfflinePaperFillReceiptArchiveCertificateError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("version") != SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveCertificateError("unsupported source schema or version")
    if source.get("decision") != "offline_paper_fill_receipt_archive_package_verified":
        raise OfflinePaperFillReceiptArchiveCertificateError("source decision invalid")
    if source.get("verification_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateError("source verification scope invalid")
    if source.get("verification_state") != "VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_PACKAGE":
        raise OfflinePaperFillReceiptArchiveCertificateError("source verification state invalid")
    if source.get("archive_package_verified") is not True:
        raise OfflinePaperFillReceiptArchiveCertificateError("archive package verification incomplete")

    observed = source.get("offline_paper_fill_receipt_archive_verification_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_receipt_archive_verification_sha256", None)
    if observed != sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveCertificateError("archive verification integrity failed")

    for field, hash_field in (
        ("verified_archive_index", "verified_archive_index_sha256"),
        ("verification_checks", "verification_checks_sha256"),
        ("verification_ledger", "verification_ledger_sha256"),
    ):
        _require_hash(source, field, hash_field)

    verification_id = source.get("fill_receipt_archive_verification_id")
    package_id = source.get("fill_receipt_archive_package_id")
    if not isinstance(verification_id, str) or not verification_id.startswith("FAV-"):
        raise OfflinePaperFillReceiptArchiveCertificateError("archive verification id invalid")
    if not isinstance(package_id, str) or not package_id.startswith("FRA-"):
        raise OfflinePaperFillReceiptArchiveCertificateError("archive package id invalid")

    index = source.get("verified_archive_index")
    if not isinstance(index, list) or not index:
        raise OfflinePaperFillReceiptArchiveCertificateError("verified archive index required")
    if source.get("verified_archived_receipt_count") != len(index):
        raise OfflinePaperFillReceiptArchiveCertificateError("verified archive receipt count mismatch")

    seen = set()
    for i, item in enumerate(index, start=1):
        if not isinstance(item, dict):
            raise OfflinePaperFillReceiptArchiveCertificateError("verified archive index entry must be an object")
        if item.get("archive_index") != i:
            raise OfflinePaperFillReceiptArchiveCertificateError("verified archive index sequence invalid")
        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-") or receipt_id in seen:
            raise OfflinePaperFillReceiptArchiveCertificateError("verified archive receipt id invalid or duplicate")
        seen.add(receipt_id)
        for key in ("receipt_sha256", "fill_id", "symbol", "side"):
            if not isinstance(item.get(key), str) or not item.get(key):
                raise OfflinePaperFillReceiptArchiveCertificateError(f"verified archive index {key} invalid")
        quantity, price = item.get("filled_quantity"), item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise OfflinePaperFillReceiptArchiveCertificateError("verified archive quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise OfflinePaperFillReceiptArchiveCertificateError("verified archive price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise OfflinePaperFillReceiptArchiveCertificateError("verified archive notional invalid")
        if item.get("verification_state") != "VERIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveCertificateError("verified archive index state invalid")

    checks = source.get("verification_checks")
    ledger = source.get("verification_ledger")
    if not isinstance(checks, list) or len(checks) != 12:
        raise OfflinePaperFillReceiptArchiveCertificateError("verification checks invalid")
    if not isinstance(ledger, list) or len(ledger) != 6:
        raise OfflinePaperFillReceiptArchiveCertificateError("verification ledger invalid")
    for i, item in enumerate(checks, start=1):
        if item.get("check_index") != i or item.get("state") not in {"PASS", "LOCKED", "ENFORCED"}:
            raise OfflinePaperFillReceiptArchiveCertificateError("verification check sequence invalid")
    for i, item in enumerate(ledger, start=1):
        if item.get("ledger_index") != i or item.get("archive_verification_id") != verification_id:
            raise OfflinePaperFillReceiptArchiveCertificateError("verification ledger sequence invalid")

    gate = source.get("verification_gate", {})
    expected_gate = {
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
        "next_version": VERSION,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise OfflinePaperFillReceiptArchiveCertificateError(f"verification_gate {key} invalid")

    for key in (
        "settlements_created", "positions_updated", "cash_updates_created",
        "portfolio_updates_created", "external_orders_submitted", "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise OfflinePaperFillReceiptArchiveCertificateError(f"mutation detected: {key}")
    for key in (
        "settlement_execution_allowed", "position_update_allowed", "cash_update_allowed",
        "portfolio_update_allowed", "external_order_submission_allowed", "broker_routing_allowed",
        "paper_broker_allowed", "live_orders_allowed", "network_allowed",
        "broker_connection_allowed", "approved_for_live", "network_used",
    ):
        if source.get(key) is not False:
            raise OfflinePaperFillReceiptArchiveCertificateError(f"unsafe source state: {key}")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise OfflinePaperFillReceiptArchiveCertificateError("safety lock invalid")
    return index


def build_certificate(
    source: Dict[str, Any],
    config: Dict[str, Any],
    certified_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    verified_index = validate_source(source)
    when = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if certified_at is None else parse_ts(certified_at)
    )
    certificate_id = "FAC-" + hashlib.sha256(
        f"{source['fill_receipt_archive_verification_id']}|"
        f"{source['offline_paper_fill_receipt_archive_verification_sha256']}|"
        f"{when}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    summary = {
        "certificate_id": certificate_id,
        "archive_verification_id": source["fill_receipt_archive_verification_id"],
        "archive_package_id": source["fill_receipt_archive_package_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "certified_receipt_count": len(verified_index),
        "certificate_result": "CERTIFIED_VERIFIED_OFFLINE_ARCHIVE",
        "certificate_effect": "INFORMATIONAL_ARCHIVE_ATTESTATION_ONLY",
        "certified_at": when,
    }

    certified_receipts = [{
        "certificate_index": i,
        "archive_index": item["archive_index"],
        "receipt_id": item["receipt_id"],
        "receipt_sha256": item["receipt_sha256"],
        "fill_id": item["fill_id"],
        "symbol": item["symbol"],
        "side": item["side"],
        "filled_quantity": item["filled_quantity"],
        "fill_price": item["fill_price"],
        "notional_value": item["notional_value"],
        "certificate_state": "CERTIFIED_VERIFIED_ARCHIVED_OFFLINE_RECEIPT",
    } for i, item in enumerate(verified_index, start=1)]

    checks = [
        {"check_index": 1, "check": "ARCHIVE_VERIFICATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "VERIFIED_ARCHIVE_INDEX_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "VERIFICATION_CHECKS_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "VERIFICATION_LEDGER_INTEGRITY", "state": "PASS"},
        {"check_index": 5, "check": "CERTIFICATE_ID_DETERMINISTIC", "state": "PASS"},
        {"check_index": 6, "check": "CERTIFICATE_SUMMARY_CREATED", "state": "PASS"},
        {"check_index": 7, "check": "CERTIFIED_RECEIPT_LINKAGES_PRESERVED", "state": "PASS"},
        {"check_index": 8, "check": "CERTIFIED_RECEIPT_NOTIONALS_PRESERVED", "state": "PASS"},
        {"check_index": 9, "check": "CERTIFICATE_CONTENT_IMMUTABLE", "state": "LOCKED"},
        {"check_index": 10, "check": "SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT", "state": "ENFORCED"},
        {"check_index": 11, "check": "NETWORK_AND_BROKER_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "ARCHIVE_VERIFICATION_ACCEPTED", "state": "PASS", "certificate_id": certificate_id},
        {"ledger_index": 2, "event": "VERIFIED_ARCHIVE_INDEX_BOUND", "state": "BOUND", "certificate_id": certificate_id},
        {"ledger_index": 3, "event": "CERTIFICATE_SUMMARY_CREATED", "state": "CREATED", "certificate_id": certificate_id},
        {"ledger_index": 4, "event": "CERTIFICATE_CONTENT_LOCKED", "state": "LOCKED", "certificate_id": certificate_id},
        {"ledger_index": 5, "event": "ACCOUNT_AND_EXTERNAL_MUTATIONS_CONFIRMED_ABSENT", "state": "ENFORCED", "certificate_id": certificate_id},
        {"ledger_index": 6, "event": "OFFLINE_ARCHIVE_CERTIFICATE_ISSUED", "state": "CERTIFIED", "certificate_id": certificate_id},
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipt_archive_certificate_issued",
        "fill_receipt_archive_certificate_id": certificate_id,
        "fill_receipt_archive_verification_id": source["fill_receipt_archive_verification_id"],
        "fill_receipt_archive_package_id": source["fill_receipt_archive_package_id"],
        "fill_receipt_verification_id": source["fill_receipt_verification_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "certificate_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_ONLY",
        "certificate_state": "ISSUED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE",
        "certified_at": when,
        "certificate_summary": summary,
        "certificate_summary_sha256": sha256_of(summary),
        "certified_receipt_count": len(certified_receipts),
        "certified_receipts": certified_receipts,
        "certified_receipts_sha256": sha256_of(certified_receipts),
        "certificate_checks": checks,
        "certificate_checks_sha256": sha256_of(checks),
        "certificate_ledger": ledger,
        "certificate_ledger_sha256": sha256_of(ledger),
        "certificate_gate": {
            "archive_certificate_issued": True,
            "archive_certificate_immutable": True,
            "certificate_effect": "INFORMATIONAL_ARCHIVE_ATTESTATION_ONLY",
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AH",
        },
        "source_archive_verification_sha256": source["offline_paper_fill_receipt_archive_verification_sha256"],
        "source_verified_archive_index_sha256": source["verified_archive_index_sha256"],
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
    output["offline_paper_fill_receipt_archive_certificate_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_receipt_archive_certificate_v75_2ag.json": output,
        "offline_paper_fill_receipt_archive_certificate_summary_v75_2ag.json": {
            "fill_receipt_archive_certificate_id": output["fill_receipt_archive_certificate_id"],
            "certificate_summary": output["certificate_summary"],
            "certificate_summary_sha256": output["certificate_summary_sha256"],
        },
        "offline_paper_fill_receipt_archive_certified_receipts_v75_2ag.json": {
            "fill_receipt_archive_certificate_id": output["fill_receipt_archive_certificate_id"],
            "certified_receipt_count": output["certified_receipt_count"],
            "certified_receipts": output["certified_receipts"],
            "certified_receipts_sha256": output["certified_receipts_sha256"],
        },
        "offline_paper_fill_receipt_archive_certificate_ledger_v75_2ag.json": {
            "fill_receipt_archive_certificate_id": output["fill_receipt_archive_certificate_id"],
            "certificate_ledger": output["certificate_ledger"],
            "certificate_ledger_sha256": output["certificate_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_receipt_archive_certificate_v75_2ag.sha256").write_text(
        output["offline_paper_fill_receipt_archive_certificate_sha256"] + "\n",
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
        print(json.dumps({
            "status": output["status"],
            "decision": output["decision"],
            "fill_receipt_archive_certificate_id": output["fill_receipt_archive_certificate_id"],
            "certificate_state": output["certificate_state"],
            "certified_receipt_count": output["certified_receipt_count"],
            "settlements_created": 0,
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_receipt_archive_certificate_sha256": output["offline_paper_fill_receipt_archive_certificate_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveCertificateError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_receipt_archive_certificate_issuance_failed",
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
