from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AH"
SCHEMA = "v75.2ah.offline_paper_fill_receipt_archive_certificate_verification.1"
SOURCE_SCHEMA = "v75.2ag.offline_paper_fill_receipt_archive_certificate.1"
SOURCE_VERSION = "75.2AG"


class OfflinePaperFillReceiptArchiveCertificateVerificationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("top-level JSON must be an object")
    return value


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("verification_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("verification_scope invalid")
    for key in (
        "require_certificate_integrity",
        "require_certificate_summary_integrity",
        "require_certified_receipts_integrity",
        "require_certificate_checks_integrity",
        "require_certificate_ledger_integrity",
        "require_deterministic_certificate_id",
        "require_receipt_notional_recalculation",
        "require_zero_settlement_and_account_mutations",
    ):
        if config.get(key) is not True:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"{key} must be true")
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
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"{key} must be false")


def _require_hash(source: Dict[str, Any], field: str, hash_field: str) -> None:
    if source.get(hash_field) != sha256_of(source.get(field)):
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"{field} integrity failed")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("version") != SOURCE_VERSION:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("unsupported source schema or version")
    if source.get("decision") != "offline_paper_fill_receipt_archive_certificate_issued":
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("source decision invalid")
    if source.get("certificate_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_ONLY":
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("source certificate scope invalid")
    if source.get("certificate_state") != "ISSUED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE":
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("source certificate state invalid")

    observed = source.get("offline_paper_fill_receipt_archive_certificate_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_receipt_archive_certificate_sha256", None)
    if observed != sha256_of(clone):
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate integrity failed")

    for field, hash_field in (
        ("certificate_summary", "certificate_summary_sha256"),
        ("certified_receipts", "certified_receipts_sha256"),
        ("certificate_checks", "certificate_checks_sha256"),
        ("certificate_ledger", "certificate_ledger_sha256"),
    ):
        _require_hash(source, field, hash_field)

    certificate_id = source.get("fill_receipt_archive_certificate_id")
    verification_id = source.get("fill_receipt_archive_verification_id")
    if not isinstance(certificate_id, str) or not certificate_id.startswith("FAC-"):
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate id invalid")
    if not isinstance(verification_id, str) or not verification_id.startswith("FAV-"):
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("archive verification id invalid")

    expected_id = "FAC-" + hashlib.sha256(
        f"{verification_id}|{source.get('source_archive_verification_sha256')}|"
        f"{source.get('certified_at')}|{SOURCE_VERSION}".encode()
    ).hexdigest()[:16].upper()
    if certificate_id != expected_id:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("deterministic certificate id mismatch")

    summary = source.get("certificate_summary")
    if not isinstance(summary, dict):
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate summary invalid")
    expected_summary = {
        "certificate_id": certificate_id,
        "archive_verification_id": verification_id,
        "archive_package_id": source.get("fill_receipt_archive_package_id"),
        "receipt_batch_id": source.get("receipt_batch_id"),
        "certified_receipt_count": source.get("certified_receipt_count"),
        "certificate_result": "CERTIFIED_VERIFIED_OFFLINE_ARCHIVE",
        "certificate_effect": "INFORMATIONAL_ARCHIVE_ATTESTATION_ONLY",
        "certified_at": source.get("certified_at"),
    }
    if summary != expected_summary:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate summary linkage invalid")

    receipts = source.get("certified_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipts required")
    if source.get("certified_receipt_count") != len(receipts):
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt count mismatch")

    seen = set()
    for i, item in enumerate(receipts, start=1):
        if not isinstance(item, dict):
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt must be an object")
        if item.get("certificate_index") != i or item.get("archive_index") != i:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt sequence invalid")
        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("FRC-") or receipt_id in seen:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt id invalid or duplicate")
        seen.add(receipt_id)
        for key in ("receipt_sha256", "fill_id", "symbol", "side"):
            if not isinstance(item.get(key), str) or not item.get(key):
                raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"certified receipt {key} invalid")
        quantity, price = item.get("filled_quantity"), item.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt price invalid")
        if item.get("notional_value") != round(float(price) * quantity, 10):
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt notional invalid")
        if item.get("certificate_state") != "CERTIFIED_VERIFIED_ARCHIVED_OFFLINE_RECEIPT":
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certified receipt state invalid")

    checks = source.get("certificate_checks")
    ledger = source.get("certificate_ledger")
    if not isinstance(checks, list) or len(checks) != 12:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate checks invalid")
    if not isinstance(ledger, list) or len(ledger) != 6:
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate ledger invalid")
    for i, item in enumerate(checks, start=1):
        if item.get("check_index") != i or item.get("state") not in {"PASS", "LOCKED", "ENFORCED"}:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate check sequence invalid")
    for i, item in enumerate(ledger, start=1):
        if item.get("ledger_index") != i or item.get("certificate_id") != certificate_id:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError("certificate ledger sequence invalid")

    gate = source.get("certificate_gate", {})
    expected_gate = {
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
        "next_version": VERSION,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"certificate_gate {key} invalid")

    for key in (
        "settlements_created", "positions_updated", "cash_updates_created",
        "portfolio_updates_created", "external_orders_submitted", "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"mutation detected: {key}")
    for key in (
        "settlement_execution_allowed", "position_update_allowed", "cash_update_allowed",
        "portfolio_update_allowed", "external_order_submission_allowed", "broker_routing_allowed",
        "paper_broker_allowed", "live_orders_allowed", "network_allowed",
        "broker_connection_allowed", "approved_for_live", "network_used",
    ):
        if source.get(key) is not False:
            raise OfflinePaperFillReceiptArchiveCertificateVerificationError(f"unsafe source state: {key}")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise OfflinePaperFillReceiptArchiveCertificateVerificationError("safety lock invalid")
    return receipts


def build_verification(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    validate_config(config)
    certified_receipts = validate_source(source)
    verification_id = "FCV-" + hashlib.sha256(
        f"{source['fill_receipt_archive_certificate_id']}|"
        f"{source['offline_paper_fill_receipt_archive_certificate_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    verified_receipts = [{
        "certificate_index": item["certificate_index"],
        "archive_index": item["archive_index"],
        "receipt_id": item["receipt_id"],
        "receipt_sha256": item["receipt_sha256"],
        "fill_id": item["fill_id"],
        "symbol": item["symbol"],
        "side": item["side"],
        "filled_quantity": item["filled_quantity"],
        "fill_price": item["fill_price"],
        "notional_value": item["notional_value"],
        "verification_state": "VERIFIED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT",
    } for item in certified_receipts]

    checks = [
        {"check_index": 1, "check": "CERTIFICATE_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "CERTIFICATE_SUMMARY_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "CERTIFIED_RECEIPTS_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "CERTIFICATE_CHECKS_INTEGRITY", "state": "PASS"},
        {"check_index": 5, "check": "CERTIFICATE_LEDGER_INTEGRITY", "state": "PASS"},
        {"check_index": 6, "check": "CERTIFICATE_ID_DETERMINISTIC", "state": "PASS"},
        {"check_index": 7, "check": "CERTIFIED_RECEIPT_LINKAGES_VERIFIED", "state": "PASS"},
        {"check_index": 8, "check": "CERTIFIED_RECEIPT_NOTIONALS_RECALCULATED", "state": "PASS"},
        {"check_index": 9, "check": "CERTIFICATE_IMMUTABILITY_CONFIRMED", "state": "LOCKED"},
        {"check_index": 10, "check": "SETTLEMENT_ACCOUNT_EXTERNAL_MUTATIONS_ABSENT", "state": "ENFORCED"},
        {"check_index": 11, "check": "NETWORK_AND_BROKER_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "CERTIFICATE_HASH_VERIFIED", "state": "PASS", "certificate_verification_id": verification_id},
        {"ledger_index": 2, "event": "CERTIFICATE_SUMMARY_VERIFIED", "state": "VERIFIED", "certificate_verification_id": verification_id},
        {"ledger_index": 3, "event": "CERTIFIED_RECEIPTS_VERIFIED", "state": "VERIFIED", "certificate_verification_id": verification_id},
        {"ledger_index": 4, "event": "CERTIFICATE_CHECKS_AND_LEDGER_VERIFIED", "state": "PASS", "certificate_verification_id": verification_id},
        {"ledger_index": 5, "event": "CERTIFICATE_IMMUTABILITY_AND_SAFETY_CONFIRMED", "state": "ENFORCED", "certificate_verification_id": verification_id},
        {"ledger_index": 6, "event": "OFFLINE_ARCHIVE_CERTIFICATE_VERIFICATION_COMPLETED", "state": "VERIFIED", "certificate_verification_id": verification_id},
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipt_archive_certificate_verified",
        "fill_receipt_archive_certificate_verification_id": verification_id,
        "fill_receipt_archive_certificate_id": source["fill_receipt_archive_certificate_id"],
        "fill_receipt_archive_verification_id": source["fill_receipt_archive_verification_id"],
        "fill_receipt_archive_package_id": source["fill_receipt_archive_package_id"],
        "fill_receipt_verification_id": source["fill_receipt_verification_id"],
        "receipt_batch_id": source["receipt_batch_id"],
        "verification_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_VERIFICATION_ONLY",
        "verification_state": "VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE",
        "archive_certificate_verified": True,
        "verified_certified_receipt_count": len(verified_receipts),
        "verified_certified_receipts": verified_receipts,
        "verified_certified_receipts_sha256": sha256_of(verified_receipts),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "archive_certificate_verified": True,
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
            "next_version": "75.2AI",
        },
        "source_archive_certificate_sha256": source["offline_paper_fill_receipt_archive_certificate_sha256"],
        "source_certificate_summary_sha256": source["certificate_summary_sha256"],
        "source_certified_receipts_sha256": source["certified_receipts_sha256"],
        "source_certificate_checks_sha256": source["certificate_checks_sha256"],
        "source_certificate_ledger_sha256": source["certificate_ledger_sha256"],
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
    output["offline_paper_fill_receipt_archive_certificate_verification_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_receipt_archive_certificate_verification_v75_2ah.json": output,
        "offline_paper_verified_fill_receipt_archive_certificate_receipts_v75_2ah.json": {
            "fill_receipt_archive_certificate_verification_id": output["fill_receipt_archive_certificate_verification_id"],
            "verified_certified_receipt_count": output["verified_certified_receipt_count"],
            "verified_certified_receipts": output["verified_certified_receipts"],
            "verified_certified_receipts_sha256": output["verified_certified_receipts_sha256"],
        },
        "offline_paper_fill_receipt_archive_certificate_verification_checks_v75_2ah.json": {
            "fill_receipt_archive_certificate_verification_id": output["fill_receipt_archive_certificate_verification_id"],
            "verification_checks": output["verification_checks"],
            "verification_checks_sha256": output["verification_checks_sha256"],
        },
        "offline_paper_fill_receipt_archive_certificate_verification_ledger_v75_2ah.json": {
            "fill_receipt_archive_certificate_verification_id": output["fill_receipt_archive_certificate_verification_id"],
            "verification_ledger": output["verification_ledger"],
            "verification_ledger_sha256": output["verification_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_receipt_archive_certificate_verification_v75_2ah.sha256").write_text(
        output["offline_paper_fill_receipt_archive_certificate_verification_sha256"] + "\n",
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
            "fill_receipt_archive_certificate_verification_id": output["fill_receipt_archive_certificate_verification_id"],
            "verification_state": output["verification_state"],
            "verified_certified_receipt_count": output["verified_certified_receipt_count"],
            "settlements_created": 0,
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_receipt_archive_certificate_verification_sha256": output["offline_paper_fill_receipt_archive_certificate_verification_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptArchiveCertificateVerificationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_receipt_archive_certificate_verification_failed",
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
