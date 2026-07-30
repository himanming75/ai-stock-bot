from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AC"
SCHEMA = "v75.2ac.offline_paper_fill_receipt.1"
SOURCE_SCHEMA = "v75.2ab.offline_paper_fill_simulation_execution_verification.1"
SOURCE_VERSION = "75.2AB"


class OfflinePaperFillReceiptError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflinePaperFillReceiptError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OfflinePaperFillReceiptError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OfflinePaperFillReceiptError("top-level JSON must be an object")
    return value


def parse_ts(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise OfflinePaperFillReceiptError(f"{name} invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OfflinePaperFillReceiptError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise OfflinePaperFillReceiptError(f"{name} must include timezone")
    return parsed


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("receipt_scope") != "OFFLINE_PAPER_FILL_RECEIPT_ARTIFACT_ONLY":
        raise OfflinePaperFillReceiptError("receipt_scope invalid")
    for key in (
        "require_verification_integrity",
        "require_verified_fill_objects_integrity",
        "require_verification_checks_integrity",
        "require_verification_ledger_integrity",
        "require_verified_execution_state",
        "require_zero_account_mutations",
        "create_receipt_artifacts",
    ):
        if config.get(key) is not True:
            raise OfflinePaperFillReceiptError(f"{key} must be true")
    for key in (
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
            raise OfflinePaperFillReceiptError(f"{key} must be false")


def _require_hash(source: Dict[str, Any], field: str, hash_field: str) -> None:
    if source.get(hash_field) != sha256_of(source.get(field)):
        raise OfflinePaperFillReceiptError(f"{field} integrity failed")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise OfflinePaperFillReceiptError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("version") != SOURCE_VERSION:
        raise OfflinePaperFillReceiptError("unsupported source schema or version")
    if source.get("decision") != "offline_paper_fill_simulation_execution_verified":
        raise OfflinePaperFillReceiptError("source decision invalid")
    if source.get("verification_scope") != "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_VERIFICATION_ONLY":
        raise OfflinePaperFillReceiptError("source verification scope invalid")
    if source.get("verification_state") != "VERIFIED_OFFLINE_FILL_OBJECT_EXECUTION":
        raise OfflinePaperFillReceiptError("source verification state invalid")
    if source.get("execution_verified") is not True:
        raise OfflinePaperFillReceiptError("execution verification incomplete")

    observed = source.get("offline_paper_fill_simulation_execution_verification_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_simulation_execution_verification_sha256", None)
    if observed != sha256_of(clone):
        raise OfflinePaperFillReceiptError("verification integrity failed")

    for field, hash_field in (
        ("verified_fill_objects", "verified_fill_objects_sha256"),
        ("verification_checks", "verification_checks_sha256"),
        ("verification_ledger", "verification_ledger_sha256"),
    ):
        _require_hash(source, field, hash_field)

    fills = source.get("verified_fill_objects")
    if not isinstance(fills, list) or not fills:
        raise OfflinePaperFillReceiptError("verified fill objects required")
    if source.get("verified_fill_object_count") != len(fills):
        raise OfflinePaperFillReceiptError("verified fill object count mismatch")

    verification_id = source.get("fill_simulation_execution_verification_id")
    execution_id = source.get("fill_simulation_execution_id")
    authorization_id = source.get("fill_simulation_authorization_id")
    for name, value, prefix in (
        ("verification id", verification_id, "FSV-"),
        ("execution id", execution_id, "FSE-"),
    ):
        if not isinstance(value, str) or not value.startswith(prefix):
            raise OfflinePaperFillReceiptError(f"{name} invalid")
    if not isinstance(authorization_id, str) or not authorization_id:
        raise OfflinePaperFillReceiptError("authorization id invalid")

    expected_verification_id = "FSV-" + hashlib.sha256(
        f"{execution_id}|{source.get('source_fill_simulation_execution_sha256')}|{SOURCE_VERSION}".encode()
    ).hexdigest()[:16].upper()
    if verification_id != expected_verification_id:
        raise OfflinePaperFillReceiptError("deterministic verification id mismatch")

    seen_fill_ids = set()
    for index, fill in enumerate(fills, start=1):
        if not isinstance(fill, dict):
            raise OfflinePaperFillReceiptError("verified fill must be an object")
        if fill.get("fill_index") != index:
            raise OfflinePaperFillReceiptError("verified fill index mismatch")
        fill_id = fill.get("fill_id")
        if not isinstance(fill_id, str) or not fill_id.startswith("FILL-") or fill_id in seen_fill_ids:
            raise OfflinePaperFillReceiptError("verified fill id invalid or duplicate")
        seen_fill_ids.add(fill_id)
        for key in (
            "fill_object_sha256",
            "paper_order_id",
            "offline_submission_id",
            "symbol",
            "side",
        ):
            if not isinstance(fill.get(key), str) or not fill.get(key):
                raise OfflinePaperFillReceiptError(f"verified fill {key} invalid")
        quantity = fill.get("filled_quantity")
        price = fill.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise OfflinePaperFillReceiptError("verified filled quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise OfflinePaperFillReceiptError("verified fill price invalid")
        if fill.get("verification_state") != "VERIFIED_OFFLINE_FILL_OBJECT_ONLY":
            raise OfflinePaperFillReceiptError("verified fill state invalid")

    checks = source.get("verification_checks")
    ledger = source.get("verification_ledger")
    if not isinstance(checks, list) or len(checks) != 12:
        raise OfflinePaperFillReceiptError("verification checks invalid")
    if not isinstance(ledger, list) or len(ledger) != 6:
        raise OfflinePaperFillReceiptError("verification ledger invalid")
    for i, item in enumerate(checks, start=1):
        if item.get("check_index") != i or item.get("state") not in {"PASS", "LOCKED", "ENFORCED"}:
            raise OfflinePaperFillReceiptError("verification check sequence invalid")
    for i, item in enumerate(ledger, start=1):
        if item.get("ledger_index") != i or item.get("verification_id") != verification_id:
            raise OfflinePaperFillReceiptError("verification ledger sequence invalid")

    gate = source.get("verification_gate", {})
    expected_gate = {
        "execution_verified": True,
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
            raise OfflinePaperFillReceiptError(f"verification_gate {key} invalid")

    for key in (
        "positions_updated",
        "cash_updates_created",
        "portfolio_updates_created",
        "external_orders_submitted",
        "broker_routes_created",
    ):
        if source.get(key) != 0:
            raise OfflinePaperFillReceiptError(f"account or external mutation detected: {key}")
    for key in (
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
            raise OfflinePaperFillReceiptError(f"unsafe source state: {key}")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise OfflinePaperFillReceiptError("safety lock invalid")
    return fills


def build_receipts(
    source: Dict[str, Any],
    config: Dict[str, Any],
    issued_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    fills = validate_source(source)
    when = datetime.now(timezone.utc).replace(microsecond=0) if issued_at is None else parse_ts(issued_at, "issued_at")
    receipt_time = when.isoformat()
    batch_id = "FRB-" + hashlib.sha256(
        f"{source['fill_simulation_execution_verification_id']}|"
        f"{source['offline_paper_fill_simulation_execution_verification_sha256']}|"
        f"{receipt_time}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    receipts = []
    for index, fill in enumerate(fills, start=1):
        receipt_id = "FRC-" + hashlib.sha256(
            f"{batch_id}|{fill['fill_id']}|{fill['fill_object_sha256']}|{VERSION}".encode()
        ).hexdigest()[:16].upper()
        receipt = {
            "receipt_index": index,
            "receipt_id": receipt_id,
            "receipt_batch_id": batch_id,
            "fill_simulation_execution_verification_id": source["fill_simulation_execution_verification_id"],
            "fill_simulation_execution_id": source["fill_simulation_execution_id"],
            "fill_simulation_authorization_id": source["fill_simulation_authorization_id"],
            "fill_id": fill["fill_id"],
            "fill_object_sha256": fill["fill_object_sha256"],
            "paper_order_id": fill["paper_order_id"],
            "offline_submission_id": fill["offline_submission_id"],
            "symbol": fill["symbol"],
            "side": fill["side"],
            "filled_quantity": fill["filled_quantity"],
            "fill_price": fill["fill_price"],
            "notional_value": round(float(fill["fill_price"]) * fill["filled_quantity"], 10),
            "currency": "USD",
            "receipt_type": "OFFLINE_PAPER_FILL_RECEIPT",
            "receipt_state": "ISSUED_OFFLINE_ARTIFACT_ONLY",
            "issued_at": receipt_time,
            "offline_only": True,
            "informational_only": True,
            "settlement_executed": False,
            "position_updated": False,
            "cash_updated": False,
            "portfolio_updated": False,
            "broker_connected": False,
            "broker_routed": False,
            "external_submission": False,
            "network_used": False,
            "approved_for_live": False,
        }
        receipt["receipt_sha256"] = sha256_of(receipt)
        receipts.append(receipt)

    checks = [
        {"check_index": 1, "check": "VERIFICATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "VERIFIED_FILL_OBJECTS_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "VERIFICATION_CHECKS_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "VERIFICATION_LEDGER_INTEGRITY", "state": "PASS"},
        {"check_index": 5, "check": "RECEIPT_IDENTITIES_DETERMINISTIC", "state": "PASS"},
        {"check_index": 6, "check": "RECEIPT_NOTIONAL_RECALCULATED", "state": "PASS"},
        {"check_index": 7, "check": "OFFLINE_RECEIPT_ARTIFACTS_CREATED", "state": "PASS"},
        {"check_index": 8, "check": "SETTLEMENT_EXECUTION_BLOCKED", "state": "ENFORCED"},
        {"check_index": 9, "check": "POSITION_CASH_PORTFOLIO_UNCHANGED", "state": "ENFORCED"},
        {"check_index": 10, "check": "BROKER_AND_EXTERNAL_SUBMISSION_BLOCKED", "state": "PASS"},
        {"check_index": 11, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "FILL_EXECUTION_VERIFICATION_ACCEPTED", "state": "PASS", "receipt_batch_id": batch_id},
        {"ledger_index": 2, "event": "VERIFIED_FILL_IDENTITIES_LOCKED", "state": "LOCKED", "receipt_batch_id": batch_id},
        {"ledger_index": 3, "event": "OFFLINE_FILL_RECEIPTS_CREATED", "state": "CREATED", "receipt_batch_id": batch_id},
        {"ledger_index": 4, "event": "SETTLEMENT_AND_ACCOUNT_MUTATIONS_SKIPPED", "state": "ENFORCED", "receipt_batch_id": batch_id},
        {"ledger_index": 5, "event": "BROKER_NETWORK_LIVE_PATHS_CONFIRMED_BLOCKED", "state": "PASS", "receipt_batch_id": batch_id},
        {"ledger_index": 6, "event": "OFFLINE_FILL_RECEIPT_BATCH_COMPLETED", "state": "ISSUED_ARTIFACT_ONLY", "receipt_batch_id": batch_id},
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipts_issued_artifact_only",
        "receipt_batch_id": batch_id,
        "fill_simulation_execution_verification_id": source["fill_simulation_execution_verification_id"],
        "fill_simulation_execution_id": source["fill_simulation_execution_id"],
        "fill_simulation_authorization_id": source["fill_simulation_authorization_id"],
        "receipt_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARTIFACT_ONLY",
        "receipt_batch_state": "ISSUED_OFFLINE_RECEIPTS_ONLY",
        "receipt_count": len(receipts),
        "receipts": receipts,
        "receipts_sha256": sha256_of(receipts),
        "receipt_checks": checks,
        "receipt_checks_sha256": sha256_of(checks),
        "receipt_ledger": ledger,
        "receipt_ledger_sha256": sha256_of(ledger),
        "receipt_gate": {
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
            "next_version": "75.2AD",
        },
        "source_fill_simulation_execution_verification_sha256": source["offline_paper_fill_simulation_execution_verification_sha256"],
        "source_verified_fill_objects_sha256": source["verified_fill_objects_sha256"],
        "source_verification_checks_sha256": source["verification_checks_sha256"],
        "source_verification_ledger_sha256": source["verification_ledger_sha256"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "issued_at": receipt_time,
        "receipts_created": len(receipts),
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
    output["offline_paper_fill_receipt_batch_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_receipt_batch_v75_2ac.json": output,
        "offline_paper_fill_receipts_v75_2ac.json": {
            "receipt_batch_id": output["receipt_batch_id"],
            "receipt_count": output["receipt_count"],
            "receipts": output["receipts"],
            "receipts_sha256": output["receipts_sha256"],
        },
        "offline_paper_fill_receipt_checks_v75_2ac.json": {
            "receipt_batch_id": output["receipt_batch_id"],
            "receipt_checks": output["receipt_checks"],
            "receipt_checks_sha256": output["receipt_checks_sha256"],
        },
        "offline_paper_fill_receipt_ledger_v75_2ac.json": {
            "receipt_batch_id": output["receipt_batch_id"],
            "receipt_ledger": output["receipt_ledger"],
            "receipt_ledger_sha256": output["receipt_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_receipt_batch_v75_2ac.sha256").write_text(
        output["offline_paper_fill_receipt_batch_sha256"] + "\n", encoding="utf-8"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--issued-at")
    args = parser.parse_args(argv)
    try:
        output = build_receipts(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.issued_at,
        )
        write_outputs(output, Path(args.output_dir))
        print(json.dumps({
            "status": output["status"],
            "decision": output["decision"],
            "receipt_batch_id": output["receipt_batch_id"],
            "receipt_batch_state": output["receipt_batch_state"],
            "receipt_count": output["receipt_count"],
            "first_receipt": output["receipts"][0],
            "settlements_created": 0,
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_receipt_batch_sha256": output["offline_paper_fill_receipt_batch_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OfflinePaperFillReceiptError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_receipt_creation_failed",
            "error": str(exc),
            "receipts_created": 0,
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
