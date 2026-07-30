from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AD"
SCHEMA = "v75.2ad.offline_paper_fill_receipt_verification.1"
SOURCE_SCHEMA = "v75.2ac.offline_paper_fill_receipt.1"
SOURCE_VERSION = "75.2AC"


class OfflinePaperFillReceiptVerificationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflinePaperFillReceiptVerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OfflinePaperFillReceiptVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OfflinePaperFillReceiptVerificationError("top-level JSON must be an object")
    return value


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("verification_scope") != "OFFLINE_PAPER_FILL_RECEIPT_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptVerificationError("verification_scope invalid")
    for key in (
        "require_receipt_batch_integrity",
        "require_receipts_integrity",
        "require_each_receipt_integrity",
        "require_receipt_checks_integrity",
        "require_receipt_ledger_integrity",
        "require_deterministic_receipt_ids",
        "require_notional_recalculation",
        "require_zero_settlement_and_account_mutations",
    ):
        if config.get(key) is not True:
            raise OfflinePaperFillReceiptVerificationError(f"{key} must be true")
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
            raise OfflinePaperFillReceiptVerificationError(f"{key} must be false")


def _require_hash(source: Dict[str, Any], field: str, hash_field: str) -> None:
    if source.get(hash_field) != sha256_of(source.get(field)):
        raise OfflinePaperFillReceiptVerificationError(f"{field} integrity failed")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise OfflinePaperFillReceiptVerificationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("version") != SOURCE_VERSION:
        raise OfflinePaperFillReceiptVerificationError("unsupported source schema or version")
    if source.get("decision") != "offline_paper_fill_receipts_issued_artifact_only":
        raise OfflinePaperFillReceiptVerificationError("source decision invalid")
    if source.get("receipt_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARTIFACT_ONLY":
        raise OfflinePaperFillReceiptVerificationError("source receipt scope invalid")
    if source.get("receipt_batch_state") != "ISSUED_OFFLINE_RECEIPTS_ONLY":
        raise OfflinePaperFillReceiptVerificationError("source receipt batch state invalid")

    observed = source.get("offline_paper_fill_receipt_batch_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_receipt_batch_sha256", None)
    if observed != sha256_of(clone):
        raise OfflinePaperFillReceiptVerificationError("receipt batch integrity failed")

    for field, hash_field in (
        ("receipts", "receipts_sha256"),
        ("receipt_checks", "receipt_checks_sha256"),
        ("receipt_ledger", "receipt_ledger_sha256"),
    ):
        _require_hash(source, field, hash_field)

    receipts = source.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise OfflinePaperFillReceiptVerificationError("receipts required")
    if source.get("receipt_count") != len(receipts) or source.get("receipts_created") != len(receipts):
        raise OfflinePaperFillReceiptVerificationError("receipt count mismatch")

    batch_id = source.get("receipt_batch_id")
    verification_id = source.get("fill_simulation_execution_verification_id")
    if not isinstance(batch_id, str) or not batch_id.startswith("FRB-"):
        raise OfflinePaperFillReceiptVerificationError("receipt batch id invalid")
    if not isinstance(verification_id, str) or not verification_id.startswith("FSV-"):
        raise OfflinePaperFillReceiptVerificationError("verification id invalid")

    expected_batch_id = "FRB-" + hashlib.sha256(
        f"{verification_id}|{source.get('source_fill_simulation_execution_verification_sha256')}|"
        f"{source.get('issued_at')}|{SOURCE_VERSION}".encode()
    ).hexdigest()[:16].upper()
    if batch_id != expected_batch_id:
        raise OfflinePaperFillReceiptVerificationError("deterministic receipt batch id mismatch")

    seen = set()
    for index, receipt in enumerate(receipts, start=1):
        if not isinstance(receipt, dict):
            raise OfflinePaperFillReceiptVerificationError("receipt must be an object")
        receipt_clone = copy.deepcopy(receipt)
        observed_receipt_hash = receipt_clone.pop("receipt_sha256", None)
        if observed_receipt_hash != sha256_of(receipt_clone):
            raise OfflinePaperFillReceiptVerificationError("receipt integrity failed")
        if receipt.get("receipt_index") != index:
            raise OfflinePaperFillReceiptVerificationError("receipt index mismatch")
        expected_receipt_id = "FRC-" + hashlib.sha256(
            f"{batch_id}|{receipt.get('fill_id')}|{receipt.get('fill_object_sha256')}|{SOURCE_VERSION}".encode()
        ).hexdigest()[:16].upper()
        if receipt.get("receipt_id") != expected_receipt_id or expected_receipt_id in seen:
            raise OfflinePaperFillReceiptVerificationError("deterministic receipt id mismatch")
        seen.add(expected_receipt_id)
        if receipt.get("receipt_batch_id") != batch_id:
            raise OfflinePaperFillReceiptVerificationError("receipt batch linkage mismatch")
        if receipt.get("fill_simulation_execution_verification_id") != verification_id:
            raise OfflinePaperFillReceiptVerificationError("receipt verification linkage mismatch")
        if receipt.get("receipt_type") != "OFFLINE_PAPER_FILL_RECEIPT":
            raise OfflinePaperFillReceiptVerificationError("receipt type invalid")
        if receipt.get("receipt_state") != "ISSUED_OFFLINE_ARTIFACT_ONLY":
            raise OfflinePaperFillReceiptVerificationError("receipt state invalid")
        quantity, price = receipt.get("filled_quantity"), receipt.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise OfflinePaperFillReceiptVerificationError("receipt quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise OfflinePaperFillReceiptVerificationError("receipt price invalid")
        if receipt.get("notional_value") != round(float(price) * quantity, 10):
            raise OfflinePaperFillReceiptVerificationError("receipt notional mismatch")
        if receipt.get("issued_at") != source.get("issued_at"):
            raise OfflinePaperFillReceiptVerificationError("receipt issued_at mismatch")
        if receipt.get("offline_only") is not True or receipt.get("informational_only") is not True:
            raise OfflinePaperFillReceiptVerificationError("receipt must be offline informational only")
        for key in (
            "settlement_executed", "position_updated", "cash_updated", "portfolio_updated",
            "broker_connected", "broker_routed", "external_submission", "network_used",
            "approved_for_live",
        ):
            if receipt.get(key) is not False:
                raise OfflinePaperFillReceiptVerificationError(f"unsafe receipt state: {key}")

    checks = source.get("receipt_checks")
    ledger = source.get("receipt_ledger")
    if not isinstance(checks, list) or len(checks) != 12:
        raise OfflinePaperFillReceiptVerificationError("receipt checks invalid")
    if not isinstance(ledger, list) or len(ledger) != 6:
        raise OfflinePaperFillReceiptVerificationError("receipt ledger invalid")
    for i, item in enumerate(checks, start=1):
        if item.get("check_index") != i or item.get("state") not in {"PASS", "LOCKED", "ENFORCED"}:
            raise OfflinePaperFillReceiptVerificationError("receipt check sequence invalid")
    for i, item in enumerate(ledger, start=1):
        if item.get("ledger_index") != i or item.get("receipt_batch_id") != batch_id:
            raise OfflinePaperFillReceiptVerificationError("receipt ledger sequence invalid")

    gate = source.get("receipt_gate", {})
    expected_gate = {
        "receipt_artifacts_created": True,
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
            raise OfflinePaperFillReceiptVerificationError(f"receipt_gate {key} invalid")

    for key in (
        "settlements_created", "positions_updated", "cash_updates_created",
        "portfolio_updates_created", "external_orders_submitted", "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise OfflinePaperFillReceiptVerificationError(f"mutation detected: {key}")
    for key in (
        "settlement_execution_allowed", "position_update_allowed", "cash_update_allowed",
        "portfolio_update_allowed", "external_order_submission_allowed", "broker_routing_allowed",
        "paper_broker_allowed", "live_orders_allowed", "network_allowed",
        "broker_connection_allowed", "approved_for_live", "network_used",
    ):
        if source.get(key) is not False:
            raise OfflinePaperFillReceiptVerificationError(f"unsafe source state: {key}")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise OfflinePaperFillReceiptVerificationError("safety lock invalid")
    return receipts


def build_verification(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    validate_config(config)
    receipts = validate_source(source)
    verification_id = "FRV-" + hashlib.sha256(
        f"{source['receipt_batch_id']}|{source['offline_paper_fill_receipt_batch_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    verified_receipts = [{
        "receipt_index": receipt["receipt_index"],
        "receipt_id": receipt["receipt_id"],
        "receipt_sha256": receipt["receipt_sha256"],
        "fill_id": receipt["fill_id"],
        "paper_order_id": receipt["paper_order_id"],
        "offline_submission_id": receipt["offline_submission_id"],
        "symbol": receipt["symbol"],
        "side": receipt["side"],
        "filled_quantity": receipt["filled_quantity"],
        "fill_price": receipt["fill_price"],
        "notional_value": receipt["notional_value"],
        "verification_state": "VERIFIED_OFFLINE_FILL_RECEIPT_ONLY",
    } for receipt in receipts]

    checks = [
        {"check_index": 1, "check": "RECEIPT_BATCH_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "RECEIPT_COLLECTION_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "INDIVIDUAL_RECEIPT_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "DETERMINISTIC_BATCH_AND_RECEIPT_IDS", "state": "PASS"},
        {"check_index": 5, "check": "RECEIPT_LINKAGES_VERIFIED", "state": "PASS"},
        {"check_index": 6, "check": "RECEIPT_NOTIONAL_RECALCULATED", "state": "PASS"},
        {"check_index": 7, "check": "RECEIPT_CHECKS_INTEGRITY", "state": "PASS"},
        {"check_index": 8, "check": "RECEIPT_LEDGER_INTEGRITY", "state": "PASS"},
        {"check_index": 9, "check": "SETTLEMENT_AND_ACCOUNT_MUTATIONS_ABSENT", "state": "ENFORCED"},
        {"check_index": 10, "check": "BROKER_EXTERNAL_SUBMISSION_BLOCKED", "state": "PASS"},
        {"check_index": 11, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "RECEIPT_BATCH_HASH_VERIFIED", "state": "PASS", "receipt_verification_id": verification_id},
        {"ledger_index": 2, "event": "OFFLINE_FILL_RECEIPTS_VERIFIED", "state": "VERIFIED", "receipt_verification_id": verification_id},
        {"ledger_index": 3, "event": "RECEIPT_IDS_AND_LINKAGES_VERIFIED", "state": "PASS", "receipt_verification_id": verification_id},
        {"ledger_index": 4, "event": "RECEIPT_NOTIONALS_VERIFIED", "state": "PASS", "receipt_verification_id": verification_id},
        {"ledger_index": 5, "event": "SETTLEMENT_ACCOUNT_MUTATIONS_CONFIRMED_ABSENT", "state": "ENFORCED", "receipt_verification_id": verification_id},
        {"ledger_index": 6, "event": "OFFLINE_FILL_RECEIPT_VERIFICATION_COMPLETED", "state": "VERIFIED", "receipt_verification_id": verification_id},
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipts_verified",
        "fill_receipt_verification_id": verification_id,
        "receipt_batch_id": source["receipt_batch_id"],
        "fill_simulation_execution_verification_id": source["fill_simulation_execution_verification_id"],
        "fill_simulation_execution_id": source["fill_simulation_execution_id"],
        "fill_simulation_authorization_id": source["fill_simulation_authorization_id"],
        "verification_scope": "OFFLINE_PAPER_FILL_RECEIPT_VERIFICATION_ONLY",
        "verification_state": "VERIFIED_OFFLINE_FILL_RECEIPTS",
        "receipts_verified": True,
        "verified_receipt_count": len(verified_receipts),
        "verified_receipts": verified_receipts,
        "verified_receipts_sha256": sha256_of(verified_receipts),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
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
            "next_version": "75.2AE",
        },
        "source_fill_receipt_batch_sha256": source["offline_paper_fill_receipt_batch_sha256"],
        "source_receipts_sha256": source["receipts_sha256"],
        "source_receipt_checks_sha256": source["receipt_checks_sha256"],
        "source_receipt_ledger_sha256": source["receipt_ledger_sha256"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "receipts_created": source["receipts_created"],
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
    output["offline_paper_fill_receipt_verification_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_receipt_verification_v75_2ad.json": output,
        "offline_paper_verified_fill_receipts_v75_2ad.json": {
            "fill_receipt_verification_id": output["fill_receipt_verification_id"],
            "verified_receipt_count": output["verified_receipt_count"],
            "verified_receipts": output["verified_receipts"],
            "verified_receipts_sha256": output["verified_receipts_sha256"],
        },
        "offline_paper_fill_receipt_verification_checks_v75_2ad.json": {
            "fill_receipt_verification_id": output["fill_receipt_verification_id"],
            "verification_checks": output["verification_checks"],
            "verification_checks_sha256": output["verification_checks_sha256"],
        },
        "offline_paper_fill_receipt_verification_ledger_v75_2ad.json": {
            "fill_receipt_verification_id": output["fill_receipt_verification_id"],
            "verification_ledger": output["verification_ledger"],
            "verification_ledger_sha256": output["verification_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_receipt_verification_v75_2ad.sha256").write_text(
        output["offline_paper_fill_receipt_verification_sha256"] + "\n", encoding="utf-8"
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
            "fill_receipt_verification_id": output["fill_receipt_verification_id"],
            "verification_state": output["verification_state"],
            "verified_receipt_count": output["verified_receipt_count"],
            "settlements_created": 0,
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_receipt_verification_sha256": output["offline_paper_fill_receipt_verification_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptVerificationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_receipt_verification_failed",
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
