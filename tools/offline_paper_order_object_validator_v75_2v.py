from __future__ import annotations
import argparse, copy, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2V"
SCHEMA = "v75.2v.offline_paper_order_object_validation.1"
SOURCE_SCHEMA = "v75.2u.offline_paper_order_generation_execution.1"

class OrderObjectValidationError(ValueError):
    pass

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OrderObjectValidationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OrderObjectValidationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OrderObjectValidationError("top-level JSON must be an object")
    return value

def parse_ts(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise OrderObjectValidationError(f"{name} invalid")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OrderObjectValidationError(f"{name} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise OrderObjectValidationError(f"{name} must include timezone")
    return dt

def expected_order_id(authorization_id: str, intent_id: str, created_at: str) -> str:
    digest = hashlib.sha256(
        f"{authorization_id}|{intent_id}|{created_at}|75.2U".encode()
    ).hexdigest()[:16].upper()
    return f"PORD-{digest}"

def validate_config(config: Dict[str, Any]) -> None:
    if config.get("validation_scope") != "OFFLINE_PAPER_ORDER_OBJECT_VALIDATION_ONLY":
        raise OrderObjectValidationError("validation_scope invalid")
    if config.get("required_order_type") != "MARKET_REFERENCE_ONLY":
        raise OrderObjectValidationError("required_order_type invalid")
    if config.get("required_time_in_force") != "DAY":
        raise OrderObjectValidationError("required_time_in_force invalid")
    if config.get("required_order_state") != "CREATED_NOT_SUBMITTED":
        raise OrderObjectValidationError("required_order_state invalid")
    if config.get("minimum_reference_price") != 0.01:
        raise OrderObjectValidationError("minimum_reference_price invalid")
    for key in (
        "require_execution_integrity",
        "require_package_integrity",
        "require_consumed_token_integrity",
        "require_order_id_recalculation",
        "require_zero_submissions",
        "require_zero_fills",
        "require_safety_lock",
    ):
        if config.get(key) is not True:
            raise OrderObjectValidationError(f"{key} must be true")
    for key in (
        "order_submission_allowed",
        "fill_simulation_allowed",
        "paper_broker_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise OrderObjectValidationError(f"{key} must be false")

def validate_source(source: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise OrderObjectValidationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise OrderObjectValidationError("unsupported source schema")
    if source.get("execution_state") != "READY_FOR_ORDER_OBJECT_VALIDATION":
        raise OrderObjectValidationError("source not ready for order object validation")
    if source.get("order_generation_executed") is not True:
        raise OrderObjectValidationError("order generation not executed")
    if source.get("authorization_state") != "CONSUMED":
        raise OrderObjectValidationError("authorization not consumed")
    if source.get("token_consumed") is not True:
        raise OrderObjectValidationError("token not consumed")

    observed = source.get("offline_paper_order_generation_execution_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_order_generation_execution_sha256", None)
    if observed != sha256_of(clone):
        raise OrderObjectValidationError("execution integrity failed")

    for field, hash_field in (
        ("paper_order_package", "paper_order_package_sha256"),
        ("consumed_authorization_token", "consumed_authorization_token_sha256"),
        ("execution_checks", "execution_checks_sha256"),
        ("execution_ledger", "execution_ledger_sha256"),
    ):
        if source.get(hash_field) != sha256_of(source.get(field)):
            raise OrderObjectValidationError(f"{field} integrity failed")

    gate = source.get("execution_gate", {})
    expected_gate = {
        "order_objects_created": True,
        "order_object_validation_allowed": True,
        "order_submission_allowed": False,
        "fill_simulation_allowed": False,
        "paper_broker_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise OrderObjectValidationError(f"execution_gate {key} invalid")

    token = source.get("consumed_authorization_token")
    if not isinstance(token, dict):
        raise OrderObjectValidationError("consumed authorization token required")
    if token.get("single_use") is not True or token.get("consumed") is not True:
        raise OrderObjectValidationError("consumed token state invalid")
    if token.get("token_state") != "CONSUMED" or not token.get("consumed_at"):
        raise OrderObjectValidationError("consumed token evidence invalid")
    parse_ts(token.get("issued_at"), "issued_at")
    parse_ts(token.get("expires_at"), "expires_at")
    parse_ts(token.get("consumed_at"), "consumed_at")
    if token.get("authorization_id") != source.get("authorization_id"):
        raise OrderObjectValidationError("token authorization identity mismatch")
    if token.get("validation_id") != source.get("validation_id"):
        raise OrderObjectValidationError("token validation identity mismatch")

    package = source.get("paper_order_package")
    if not isinstance(package, dict):
        raise OrderObjectValidationError("paper order package required")
    if package.get("immutable") is not True or package.get("offline_only") is not True:
        raise OrderObjectValidationError("paper order package must be immutable and offline-only")
    if package.get("network_source") is not False:
        raise OrderObjectValidationError("paper order package network source invalid")
    orders = package.get("paper_orders")
    if not isinstance(orders, list) or not orders:
        raise OrderObjectValidationError("paper orders required")
    if package.get("paper_order_count") != len(orders):
        raise OrderObjectValidationError("paper order count mismatch")
    if source.get("order_objects_created") != len(orders):
        raise OrderObjectValidationError("source order object count mismatch")

    if token.get("authorized_order_intent_ids") != [o.get("order_intent_id") for o in orders]:
        raise OrderObjectValidationError("token order intent identity lock mismatch")

    order_ids = set()
    intent_ids = set()
    for order in orders:
        oid = order.get("paper_order_id")
        iid = order.get("order_intent_id")
        if not isinstance(oid, str) or not re.fullmatch(r"PORD-[0-9A-F]{16}", oid):
            raise OrderObjectValidationError("invalid paper_order_id format")
        if oid in order_ids:
            raise OrderObjectValidationError("duplicate paper_order_id")
        order_ids.add(oid)
        if not isinstance(iid, str) or not iid.startswith("INT-"):
            raise OrderObjectValidationError("invalid order_intent_id")
        if iid in intent_ids:
            raise OrderObjectValidationError("duplicate order_intent_id")
        intent_ids.add(iid)

        created_at = order.get("created_at")
        parse_ts(created_at, "order.created_at")
        if oid != expected_order_id(source["authorization_id"], iid, created_at):
            raise OrderObjectValidationError("paper_order_id recalculation failed")
        if order.get("authorization_id") != source.get("authorization_id"):
            raise OrderObjectValidationError("order authorization identity mismatch")
        if order.get("symbol") != "SPY":
            raise OrderObjectValidationError("unexpected symbol")
        if order.get("side") not in ("BUY", "SELL"):
            raise OrderObjectValidationError("invalid side")
        if isinstance(order.get("quantity"), bool) or order.get("quantity") != 1:
            raise OrderObjectValidationError("quantity policy failed")
        if order.get("order_type") != config["required_order_type"]:
            raise OrderObjectValidationError("order type invalid")
        if order.get("time_in_force") != config["required_time_in_force"]:
            raise OrderObjectValidationError("time in force invalid")
        if order.get("order_state") != config["required_order_state"]:
            raise OrderObjectValidationError("order state invalid")
        price = order.get("reference_price")
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise OrderObjectValidationError("reference price invalid")
        if float(price) < config["minimum_reference_price"]:
            raise OrderObjectValidationError("reference price below minimum")
        if order.get("offline_paper_object") is not True:
            raise OrderObjectValidationError("offline paper object flag invalid")
        for key in ("submitted", "filled", "fill_simulated", "broker_routed", "network_used", "external_side_effects"):
            if order.get(key) is not False:
                raise OrderObjectValidationError(f"unsafe order state: {key}")

    for key in (
        "order_submission_allowed",
        "fill_simulation_allowed",
        "paper_broker_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
    ):
        if source.get(key) is not False:
            raise OrderObjectValidationError(f"{key} must be false")
    if source.get("orders_submitted") != 0 or source.get("fills_created") != 0:
        raise OrderObjectValidationError("submission or fill side effect detected")
    if package.get("orders_submitted") != 0 or package.get("fills_created") != 0:
        raise OrderObjectValidationError("package submission or fill side effect detected")
    if source.get("approved_for_live") is not False or source.get("network_used") is not False:
        raise OrderObjectValidationError("safety violation")
    lock = source.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise OrderObjectValidationError("safety lock invalid")
    return orders

def build_validation(source: Dict[str, Any], config: Dict[str, Any], validated_at: Optional[str] = None) -> Dict[str, Any]:
    validate_config(config)
    orders = validate_source(source, config)
    when = datetime.now(timezone.utc).replace(microsecond=0) if validated_at is None else parse_ts(validated_at, "validated_at")
    ts = when.isoformat()
    validation_id = "OOV-" + hashlib.sha256(
        f"{source['execution_id']}|{source['paper_order_package_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    validated_orders = []
    for order in orders:
        validated_orders.append({
            "paper_order_id": order["paper_order_id"],
            "order_intent_id": order["order_intent_id"],
            "authorization_id": order["authorization_id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "quantity": order["quantity"],
            "order_type": order["order_type"],
            "time_in_force": order["time_in_force"],
            "reference_price": order["reference_price"],
            "order_state": order["order_state"],
            "submitted": False,
            "filled": False,
            "fill_simulated": False,
            "broker_routed": False,
            "network_used": False,
            "validation_state": "PASS",
        })

    checks = [
        {"check_index": 1, "check": "ORDER_GENERATION_EXECUTION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "PAPER_ORDER_PACKAGE_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "CONSUMED_TOKEN_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "PAPER_ORDER_COUNT_CONSISTENCY", "state": "PASS"},
        {"check_index": 5, "check": "PAPER_ORDER_ID_RECALCULATION", "state": "PASS"},
        {"check_index": 6, "check": "ORDER_INTENT_IDENTITY_LOCK", "state": "LOCKED"},
        {"check_index": 7, "check": "ORDER_TERMS_POLICY", "state": "PASS"},
        {"check_index": 8, "check": "REFERENCE_PRICE_VALIDITY", "state": "PASS"},
        {"check_index": 9, "check": "ORDER_SUBMISSION_NOT_STARTED", "state": "PASS"},
        {"check_index": 10, "check": "FILL_SIMULATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 11, "check": "NETWORK_AND_BROKER_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "ORDER_GENERATION_EXECUTION_VERIFIED", "state": "PASS", "validation_id": validation_id},
        {"ledger_index": 2, "event": "PAPER_ORDER_PACKAGE_VERIFIED", "state": "PASS", "validation_id": validation_id},
        {"ledger_index": 3, "event": "PAPER_ORDER_IDENTITIES_RECALCULATED", "state": "PASS", "validation_id": validation_id},
        {"ledger_index": 4, "event": "ORDER_OBJECT_POLICY_VERIFIED", "state": "PASS", "validation_id": validation_id},
        {"ledger_index": 5, "event": "SAFETY_LOCKS_RECONFIRMED", "state": "ENFORCED", "validation_id": validation_id},
        {"ledger_index": 6, "event": "ORDER_OBJECT_VALIDATION_COMPLETED", "state": "READY_FOR_ORDER_SUBMISSION_AUTHORIZATION", "validation_id": validation_id},
    ]

    out = {
        "status": "PASS",
        "decision": "offline_paper_order_objects_validated",
        "validation_id": validation_id,
        "validation_state": "READY_FOR_ORDER_SUBMISSION_AUTHORIZATION",
        "order_objects_validated": True,
        "validated_order_count": len(validated_orders),
        "validated_orders": validated_orders,
        "validated_orders_sha256": sha256_of(validated_orders),
        "validation_checks": checks,
        "validation_checks_sha256": sha256_of(checks),
        "validation_ledger": ledger,
        "validation_ledger_sha256": sha256_of(ledger),
        "source_order_generation_execution_sha256": source["offline_paper_order_generation_execution_sha256"],
        "source_paper_order_package_sha256": source["paper_order_package_sha256"],
        "source_order_generation_authorization_sha256": source["source_order_generation_authorization_sha256"],
        "source_order_intent_validation_sha256": source["source_order_intent_validation_sha256"],
        "source_order_intent_execution_sha256": source["source_order_intent_execution_sha256"],
        "execution_id": source["execution_id"],
        "authorization_id": source["authorization_id"],
        "source_execution_id": source["source_execution_id"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "validation_gate": {
            "order_objects_validated": True,
            "order_submission_authorization_allowed": True,
            "order_submission_allowed": False,
            "fill_simulation_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2W",
        },
        "order_submission_allowed": False,
        "fill_simulation_allowed": False,
        "paper_broker_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "fills_created": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(source["safety_lock"]),
        "validated_at": ts,
        "schema_version": SCHEMA,
        "version": VERSION,
    }
    out["offline_paper_order_object_validation_sha256"] = sha256_of(out)
    return out

def write_outputs(out: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_order_object_validation_v75_2v.json": out,
        "offline_paper_validated_order_objects_v75_2v.json": {
            "validation_id": out["validation_id"],
            "validated_order_count": out["validated_order_count"],
            "validated_orders": out["validated_orders"],
            "validated_orders_sha256": out["validated_orders_sha256"],
        },
        "offline_paper_order_object_validation_checks_v75_2v.json": {
            "validation_id": out["validation_id"],
            "validation_checks": out["validation_checks"],
            "validation_checks_sha256": out["validation_checks_sha256"],
        },
        "offline_paper_order_object_validation_ledger_v75_2v.json": {
            "validation_id": out["validation_id"],
            "validation_ledger": out["validation_ledger"],
            "validation_ledger_sha256": out["validation_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_order_object_validation_v75_2v.sha256").write_text(
        out["offline_paper_order_object_validation_sha256"] + "\n", encoding="utf-8"
    )

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--validated-at")
    args = parser.parse_args(argv)
    try:
        out = build_validation(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.validated_at,
        )
        write_outputs(out, Path(args.output_dir))
        first = out["validated_orders"][0]
        print(json.dumps({
            "status": out["status"],
            "decision": out["decision"],
            "validation_id": out["validation_id"],
            "validation_state": out["validation_state"],
            "validated_order_count": out["validated_order_count"],
            "first_validated_order": first,
            "order_submission_authorization_allowed": True,
            "order_submission_allowed": False,
            "orders_submitted": 0,
            "fill_simulation_allowed": False,
            "fills_created": 0,
            "paper_broker_allowed": False,
            "network_allowed": False,
            "approved_for_live": False,
            "network_used": False,
            "offline_paper_order_object_validation_sha256": out["offline_paper_order_object_validation_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OrderObjectValidationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_order_object_validation_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "fills_created": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
