from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AB"
SCHEMA = "v75.2ab.offline_paper_fill_simulation_execution_verification.1"
SOURCE_SCHEMA = "v75.2aa.offline_paper_fill_simulation_execution.1"
SOURCE_VERSION = "75.2AA"


class FillSimulationExecutionVerificationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FillSimulationExecutionVerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FillSimulationExecutionVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FillSimulationExecutionVerificationError("top-level JSON must be an object")
    return value


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("verification_scope") != "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_VERIFICATION_ONLY":
        raise FillSimulationExecutionVerificationError("verification_scope invalid")
    for key in (
        "require_execution_integrity",
        "require_fill_objects_integrity",
        "require_each_fill_object_integrity",
        "require_consumed_token_integrity",
        "require_execution_checks_integrity",
        "require_execution_ledger_integrity",
        "require_deterministic_fill_ids",
        "require_zero_account_mutations",
    ):
        if config.get(key) is not True:
            raise FillSimulationExecutionVerificationError(f"{key} must be true")
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
            raise FillSimulationExecutionVerificationError(f"{key} must be false")


def _require_hash(source: Dict[str, Any], field: str, hash_field: str) -> None:
    if source.get(hash_field) != sha256_of(source.get(field)):
        raise FillSimulationExecutionVerificationError(f"{field} integrity failed")


def validate_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise FillSimulationExecutionVerificationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("version") != SOURCE_VERSION:
        raise FillSimulationExecutionVerificationError("unsupported source schema or version")
    if source.get("decision") != "offline_paper_fill_simulation_executed_object_only":
        raise FillSimulationExecutionVerificationError("source decision invalid")
    if source.get("execution_scope") != "OFFLINE_PAPER_FILL_OBJECT_CREATION_ONLY":
        raise FillSimulationExecutionVerificationError("source execution scope invalid")
    if source.get("execution_state") != "EXECUTED_FILL_OBJECT_ONLY":
        raise FillSimulationExecutionVerificationError("source execution state invalid")
    if source.get("fill_simulation_executed") is not True or source.get("fill_object_creation_executed") is not True:
        raise FillSimulationExecutionVerificationError("fill object execution incomplete")

    observed = source.get("offline_paper_fill_simulation_execution_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_simulation_execution_sha256", None)
    if observed != sha256_of(clone):
        raise FillSimulationExecutionVerificationError("execution integrity failed")

    for field, hash_field in (
        ("fill_objects", "fill_objects_sha256"),
        ("consumed_authorization_token", "consumed_authorization_token_sha256"),
        ("execution_checks", "execution_checks_sha256"),
        ("execution_ledger", "execution_ledger_sha256"),
    ):
        _require_hash(source, field, hash_field)

    fills = source.get("fill_objects")
    if not isinstance(fills, list) or not fills:
        raise FillSimulationExecutionVerificationError("fill objects required")
    if source.get("fill_object_count") != len(fills):
        raise FillSimulationExecutionVerificationError("fill object count mismatch")
    if source.get("fill_objects_created") != len(fills) or source.get("fills_created") != len(fills):
        raise FillSimulationExecutionVerificationError("fill counters mismatch")

    execution_id = source.get("fill_simulation_execution_id")
    authorization_id = source.get("fill_simulation_authorization_id")
    if not isinstance(execution_id, str) or not execution_id.startswith("FSE-"):
        raise FillSimulationExecutionVerificationError("execution id invalid")
    if not isinstance(authorization_id, str) or not authorization_id:
        raise FillSimulationExecutionVerificationError("authorization id invalid")

    expected_execution_id = "FSE-" + hashlib.sha256(
        f"{authorization_id}|{source.get('source_authorization_token_sha256')}|{source.get('executed_at')}|{SOURCE_VERSION}".encode()
    ).hexdigest()[:16].upper()
    if execution_id != expected_execution_id:
        raise FillSimulationExecutionVerificationError("deterministic execution id mismatch")

    seen = set()
    for index, fill in enumerate(fills, start=1):
        if not isinstance(fill, dict):
            raise FillSimulationExecutionVerificationError("fill object must be an object")
        fill_clone = copy.deepcopy(fill)
        observed_fill_hash = fill_clone.pop("fill_object_sha256", None)
        if observed_fill_hash != sha256_of(fill_clone):
            raise FillSimulationExecutionVerificationError("fill object integrity failed")
        if fill.get("fill_index") != index:
            raise FillSimulationExecutionVerificationError("fill index mismatch")
        expected_fill_id = "FILL-" + hashlib.sha256(
            f"{authorization_id}|{fill.get('paper_order_id')}|{fill.get('offline_submission_id')}|{SOURCE_VERSION}".encode()
        ).hexdigest()[:16].upper()
        if fill.get("fill_id") != expected_fill_id or expected_fill_id in seen:
            raise FillSimulationExecutionVerificationError("deterministic fill id mismatch")
        seen.add(expected_fill_id)
        if fill.get("fill_simulation_execution_id") != execution_id:
            raise FillSimulationExecutionVerificationError("fill execution id mismatch")
        if fill.get("fill_simulation_authorization_id") != authorization_id:
            raise FillSimulationExecutionVerificationError("fill authorization id mismatch")
        if fill.get("fill_type") != "OFFLINE_PAPER_REFERENCE_FILL":
            raise FillSimulationExecutionVerificationError("fill type invalid")
        if fill.get("fill_state") != "FILLED_OFFLINE_OBJECT_ONLY":
            raise FillSimulationExecutionVerificationError("fill state invalid")
        if fill.get("fill_price_policy") != "REFERENCE_PRICE_ONLY":
            raise FillSimulationExecutionVerificationError("fill price policy invalid")
        if fill.get("fill_quantity_policy") != "FULL_QUANTITY_ONLY":
            raise FillSimulationExecutionVerificationError("fill quantity policy invalid")
        quantity, price = fill.get("filled_quantity"), fill.get("fill_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise FillSimulationExecutionVerificationError("filled quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise FillSimulationExecutionVerificationError("fill price invalid")
        if fill.get("notional_value") != round(float(price) * quantity, 10):
            raise FillSimulationExecutionVerificationError("notional value mismatch")
        if fill.get("simulated_at") != source.get("executed_at"):
            raise FillSimulationExecutionVerificationError("fill timestamp mismatch")
        if fill.get("offline_only") is not True:
            raise FillSimulationExecutionVerificationError("fill must be offline only")
        for key in ("broker_connected", "broker_routed", "external_submission", "network_used",
                    "position_updated", "cash_updated", "portfolio_updated", "approved_for_live"):
            if fill.get(key) is not False:
                raise FillSimulationExecutionVerificationError(f"unsafe fill state: {key}")

    token = source.get("consumed_authorization_token")
    if not isinstance(token, dict):
        raise FillSimulationExecutionVerificationError("consumed token required")
    if token.get("consumed") is not True or token.get("consumed_at") != source.get("executed_at"):
        raise FillSimulationExecutionVerificationError("token consumption invalid")
    if token.get("token_state") != "CONSUMED_BY_OFFLINE_FILL_SIMULATION":
        raise FillSimulationExecutionVerificationError("token state invalid")
    if token.get("consumed_by_execution_id") != execution_id:
        raise FillSimulationExecutionVerificationError("token consumer mismatch")
    if token.get("token_sha256") != source.get("source_authorization_token_sha256"):
        raise FillSimulationExecutionVerificationError("source token identity mismatch")

    checks = source.get("execution_checks")
    ledger = source.get("execution_ledger")
    if not isinstance(checks, list) or len(checks) != 12:
        raise FillSimulationExecutionVerificationError("execution checks invalid")
    if not isinstance(ledger, list) or len(ledger) != 6:
        raise FillSimulationExecutionVerificationError("execution ledger invalid")
    for i, item in enumerate(checks, start=1):
        if item.get("check_index") != i or item.get("state") not in {"PASS", "LOCKED", "ENFORCED"}:
            raise FillSimulationExecutionVerificationError("execution check sequence invalid")
    for i, item in enumerate(ledger, start=1):
        if item.get("ledger_index") != i or item.get("execution_id") != execution_id:
            raise FillSimulationExecutionVerificationError("execution ledger sequence invalid")

    gate = source.get("execution_gate", {})
    expected_gate = {
        "fill_object_creation_completed": True,
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
            raise FillSimulationExecutionVerificationError(f"execution_gate {key} invalid")

    for key in ("positions_updated", "cash_updates_created", "portfolio_updates_created",
                "external_orders_submitted", "broker_routes_created"):
        if source.get(key) != 0:
            raise FillSimulationExecutionVerificationError(f"account or external mutation detected: {key}")
    for key in ("position_update_allowed", "cash_update_allowed", "portfolio_update_allowed",
                "external_order_submission_allowed", "broker_routing_allowed", "paper_broker_allowed",
                "live_orders_allowed", "network_allowed", "broker_connection_allowed",
                "approved_for_live", "network_used"):
        if source.get(key) is not False:
            raise FillSimulationExecutionVerificationError(f"unsafe source state: {key}")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise FillSimulationExecutionVerificationError("safety lock invalid")
    return fills


def build_verification(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    validate_config(config)
    fills = validate_source(source)
    verification_id = "FSV-" + hashlib.sha256(
        f"{source['fill_simulation_execution_id']}|{source['offline_paper_fill_simulation_execution_sha256']}|{VERSION}".encode()
    ).hexdigest()[:16].upper()
    verified_fills = [{
        "fill_index": fill["fill_index"],
        "fill_id": fill["fill_id"],
        "fill_object_sha256": fill["fill_object_sha256"],
        "paper_order_id": fill["paper_order_id"],
        "offline_submission_id": fill["offline_submission_id"],
        "symbol": fill["symbol"],
        "side": fill["side"],
        "filled_quantity": fill["filled_quantity"],
        "fill_price": fill["fill_price"],
        "verification_state": "VERIFIED_OFFLINE_FILL_OBJECT_ONLY",
    } for fill in fills]
    checks = [
        {"check_index": 1, "check": "EXECUTION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "FILL_OBJECT_COLLECTION_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "INDIVIDUAL_FILL_OBJECT_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "DETERMINISTIC_EXECUTION_AND_FILL_IDS", "state": "PASS"},
        {"check_index": 5, "check": "CONSUMED_TOKEN_INTEGRITY", "state": "PASS"},
        {"check_index": 6, "check": "EXECUTION_CHECKS_INTEGRITY", "state": "PASS"},
        {"check_index": 7, "check": "EXECUTION_LEDGER_INTEGRITY", "state": "PASS"},
        {"check_index": 8, "check": "REFERENCE_PRICE_AND_FULL_QUANTITY_VERIFIED", "state": "LOCKED"},
        {"check_index": 9, "check": "POSITION_CASH_PORTFOLIO_UNCHANGED", "state": "ENFORCED"},
        {"check_index": 10, "check": "BROKER_EXTERNAL_SUBMISSION_BLOCKED", "state": "PASS"},
        {"check_index": 11, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "FILL_SIMULATION_EXECUTION_HASH_VERIFIED", "state": "PASS", "verification_id": verification_id},
        {"ledger_index": 2, "event": "OFFLINE_FILL_OBJECTS_VERIFIED", "state": "VERIFIED", "verification_id": verification_id},
        {"ledger_index": 3, "event": "CONSUMED_TOKEN_VERIFIED", "state": "VERIFIED", "verification_id": verification_id},
        {"ledger_index": 4, "event": "EXECUTION_CHECKS_AND_LEDGER_VERIFIED", "state": "PASS", "verification_id": verification_id},
        {"ledger_index": 5, "event": "ACCOUNT_MUTATIONS_CONFIRMED_ABSENT", "state": "ENFORCED", "verification_id": verification_id},
        {"ledger_index": 6, "event": "OFFLINE_FILL_SIMULATION_EXECUTION_VERIFICATION_COMPLETED", "state": "VERIFIED", "verification_id": verification_id},
    ]
    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_simulation_execution_verified",
        "fill_simulation_execution_verification_id": verification_id,
        "fill_simulation_execution_id": source["fill_simulation_execution_id"],
        "fill_simulation_authorization_id": source["fill_simulation_authorization_id"],
        "verification_scope": "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_VERIFICATION_ONLY",
        "verification_state": "VERIFIED_OFFLINE_FILL_OBJECT_EXECUTION",
        "execution_verified": True,
        "verified_fill_object_count": len(verified_fills),
        "verified_fill_objects": verified_fills,
        "verified_fill_objects_sha256": sha256_of(verified_fills),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "execution_verified": True,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AC",
        },
        "source_fill_simulation_execution_sha256": source["offline_paper_fill_simulation_execution_sha256"],
        "source_fill_objects_sha256": source["fill_objects_sha256"],
        "source_consumed_authorization_token_sha256": source["consumed_authorization_token_sha256"],
        "source_execution_checks_sha256": source["execution_checks_sha256"],
        "source_execution_ledger_sha256": source["execution_ledger_sha256"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "fill_objects_created": source["fill_objects_created"],
        "fills_created": source["fills_created"],
        "positions_updated": 0,
        "cash_updates_created": 0,
        "portfolio_updates_created": 0,
        "external_orders_submitted": 0,
        "broker_routes_created": 0,
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
    output["offline_paper_fill_simulation_execution_verification_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_simulation_execution_verification_v75_2ab.json": output,
        "offline_paper_verified_fill_objects_v75_2ab.json": {
            "fill_simulation_execution_verification_id": output["fill_simulation_execution_verification_id"],
            "verified_fill_object_count": output["verified_fill_object_count"],
            "verified_fill_objects": output["verified_fill_objects"],
            "verified_fill_objects_sha256": output["verified_fill_objects_sha256"],
        },
        "offline_paper_fill_simulation_execution_verification_checks_v75_2ab.json": {
            "fill_simulation_execution_verification_id": output["fill_simulation_execution_verification_id"],
            "verification_checks": output["verification_checks"],
            "verification_checks_sha256": output["verification_checks_sha256"],
        },
        "offline_paper_fill_simulation_execution_verification_ledger_v75_2ab.json": {
            "fill_simulation_execution_verification_id": output["fill_simulation_execution_verification_id"],
            "verification_ledger": output["verification_ledger"],
            "verification_ledger_sha256": output["verification_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_simulation_execution_verification_v75_2ab.sha256").write_text(
        output["offline_paper_fill_simulation_execution_verification_sha256"] + "\n", encoding="utf-8"
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
            "fill_simulation_execution_verification_id": output["fill_simulation_execution_verification_id"],
            "verification_state": output["verification_state"],
            "verified_fill_object_count": output["verified_fill_object_count"],
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_simulation_execution_verification_sha256": output["offline_paper_fill_simulation_execution_verification_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (FillSimulationExecutionVerificationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_simulation_execution_verification_failed",
            "error": str(exc),
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
