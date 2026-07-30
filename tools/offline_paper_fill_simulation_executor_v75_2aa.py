from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2AA"
SCHEMA = "v75.2aa.offline_paper_fill_simulation_execution.1"
SOURCE_SCHEMA = "v75.2z.offline_paper_fill_simulation_authorization.1"


class FillSimulationExecutionError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FillSimulationExecutionError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FillSimulationExecutionError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FillSimulationExecutionError("top-level JSON must be an object")
    return value


def parse_ts(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise FillSimulationExecutionError(f"{name} invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FillSimulationExecutionError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise FillSimulationExecutionError(f"{name} must include timezone")
    return parsed


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("execution_scope") != "OFFLINE_PAPER_FILL_OBJECT_CREATION_ONLY":
        raise FillSimulationExecutionError("execution_scope invalid")
    if config.get("fill_price_policy") != "REFERENCE_PRICE_ONLY":
        raise FillSimulationExecutionError("fill_price_policy invalid")
    if config.get("fill_quantity_policy") != "FULL_QUANTITY_ONLY":
        raise FillSimulationExecutionError("fill_quantity_policy invalid")
    for key in (
        "require_authorization_integrity",
        "require_authorized_targets_integrity",
        "require_single_use_token",
        "require_unconsumed_token",
        "require_unexpired_token",
        "require_reference_price_lock",
        "require_full_quantity_lock",
        "create_fill_objects",
    ):
        if config.get(key) is not True:
            raise FillSimulationExecutionError(f"{key} must be true")
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
            raise FillSimulationExecutionError(f"{key} must be false")


def validate_source(source: Dict[str, Any], executed_at: datetime) -> List[Dict[str, Any]]:
    if source.get("status") != "PASS":
        raise FillSimulationExecutionError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise FillSimulationExecutionError("unsupported source schema")
    if source.get("authorization_state") != "AUTHORIZED_NOT_EXECUTED":
        raise FillSimulationExecutionError("authorization is not executable")
    if source.get("fill_simulation_authorized") is not True:
        raise FillSimulationExecutionError("fill simulation is not authorized")
    if source.get("fill_simulation_execution_allowed") is not True:
        raise FillSimulationExecutionError("fill simulation execution is not allowed")
    if source.get("fill_simulation_executed") is not False:
        raise FillSimulationExecutionError("fill simulation already executed")

    observed = source.get("offline_paper_fill_simulation_authorization_sha256")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_fill_simulation_authorization_sha256", None)
    if observed != sha256_of(clone):
        raise FillSimulationExecutionError("authorization integrity failed")

    targets = source.get("authorized_fill_simulation_targets")
    if not isinstance(targets, list) or not targets:
        raise FillSimulationExecutionError("authorized fill simulation targets required")
    if source.get("authorized_target_count") != len(targets):
        raise FillSimulationExecutionError("authorized target count mismatch")
    if source.get("authorized_fill_simulation_targets_sha256") != sha256_of(targets):
        raise FillSimulationExecutionError("authorized targets integrity failed")

    token = source.get("fill_simulation_authorization_token")
    if not isinstance(token, dict):
        raise FillSimulationExecutionError("authorization token required")
    if source.get("fill_simulation_authorization_token_sha256") != sha256_of(token):
        raise FillSimulationExecutionError("authorization token envelope integrity failed")
    token_material = {
        key: token[key]
        for key in (
            "fill_simulation_authorization_id",
            "submission_validation_id",
            "issued_at",
            "expires_at",
            "nonce",
            "scope",
            "authorized_offline_submission_ids",
            "authorized_paper_order_ids",
            "fill_price_policy",
            "fill_quantity_policy",
        )
    }
    if token.get("token_sha256") != sha256_of(token_material):
        raise FillSimulationExecutionError("authorization token integrity failed")
    if token.get("scope") != "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY":
        raise FillSimulationExecutionError("authorization token scope invalid")
    if token.get("single_use") is not True:
        raise FillSimulationExecutionError("authorization token must be single-use")
    if token.get("consumed") is not False or token.get("consumed_at") is not None:
        raise FillSimulationExecutionError("authorization token already consumed")
    if token.get("token_state") != "ISSUED_NOT_CONSUMED":
        raise FillSimulationExecutionError("authorization token state invalid")
    if token.get("fill_price_policy") != "REFERENCE_PRICE_ONLY":
        raise FillSimulationExecutionError("token fill price policy invalid")
    if token.get("fill_quantity_policy") != "FULL_QUANTITY_ONLY":
        raise FillSimulationExecutionError("token fill quantity policy invalid")
    if executed_at < parse_ts(token.get("issued_at"), "issued_at"):
        raise FillSimulationExecutionError("execution precedes authorization issuance")
    if executed_at > parse_ts(token.get("expires_at"), "expires_at"):
        raise FillSimulationExecutionError("authorization token expired")

    expected_submission_ids = [target.get("offline_submission_id") for target in targets]
    expected_order_ids = [target.get("paper_order_id") for target in targets]
    if token.get("authorized_offline_submission_ids") != expected_submission_ids:
        raise FillSimulationExecutionError("authorized offline submission ids mismatch")
    if token.get("authorized_paper_order_ids") != expected_order_ids:
        raise FillSimulationExecutionError("authorized paper order ids mismatch")

    gate = source.get("authorization_gate", {})
    expected_gate = {
        "fill_simulation_authorized": True,
        "fill_simulation_execution_allowed": True,
        "fill_simulation_allowed": False,
        "fill_object_creation_allowed": False,
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
            raise FillSimulationExecutionError(f"authorization_gate {key} invalid")

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
    ):
        if source.get(key) is not False:
            raise FillSimulationExecutionError(f"unsafe source state: {key}")
    for key in (
        "positions_updated",
        "cash_updates_created",
        "portfolio_updates_created",
        "external_orders_submitted",
        "broker_routes_created",
        "fill_objects_created",
        "fills_created",
    ):
        if source.get(key) != 0:
            raise FillSimulationExecutionError(f"source counter must be zero: {key}")
    if source.get("approved_for_live") is not False or source.get("network_used") is not False:
        raise FillSimulationExecutionError("source safety violation")
    if source.get("safety_lock", {}).get("lock_state") != "ENFORCED":
        raise FillSimulationExecutionError("safety lock invalid")

    seen_fill_ids = set()
    for target in targets:
        for key in ("offline_submission_id", "paper_order_id", "order_intent_id", "authorization_id", "symbol", "side"):
            if not isinstance(target.get(key), str) or not target.get(key):
                raise FillSimulationExecutionError(f"target {key} invalid")
        if target.get("current_order_state") != "SUBMITTED_OFFLINE_REFERENCE":
            raise FillSimulationExecutionError("target order state invalid")
        if target.get("order_type") != "MARKET_REFERENCE_ONLY" or target.get("time_in_force") != "DAY":
            raise FillSimulationExecutionError("unsupported target order policy")
        quantity = target.get("quantity")
        price = target.get("reference_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise FillSimulationExecutionError("target quantity invalid")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or float(price) <= 0:
            raise FillSimulationExecutionError("target reference price invalid")
        if target.get("fill_price_policy") != "REFERENCE_PRICE_ONLY":
            raise FillSimulationExecutionError("target fill price policy invalid")
        if target.get("fill_quantity_policy") != "FULL_QUANTITY_ONLY":
            raise FillSimulationExecutionError("target fill quantity policy invalid")
        if target.get("fill_simulation_execution_authorized") is not True:
            raise FillSimulationExecutionError("target execution authorization missing")
        for key in ("fill_object_created", "fill_simulated", "filled", "position_updated", "cash_updated", "portfolio_updated"):
            if target.get(key) is not False:
                raise FillSimulationExecutionError(f"target already mutated: {key}")
        fill_id = "FILL-" + hashlib.sha256(
            f"{source['fill_simulation_authorization_id']}|{target['paper_order_id']}|{target['offline_submission_id']}|{VERSION}".encode()
        ).hexdigest()[:16].upper()
        if fill_id in seen_fill_ids:
            raise FillSimulationExecutionError("duplicate deterministic fill id")
        seen_fill_ids.add(fill_id)
    return targets


def build_execution(source: Dict[str, Any], config: Dict[str, Any], executed_at: Optional[str] = None) -> Dict[str, Any]:
    validate_config(config)
    when = datetime.now(timezone.utc).replace(microsecond=0) if executed_at is None else parse_ts(executed_at, "executed_at")
    targets = validate_source(source, when)
    execution_time = when.isoformat()
    execution_id = "FSE-" + hashlib.sha256(
        f"{source['fill_simulation_authorization_id']}|{source['fill_simulation_authorization_token']['token_sha256']}|{execution_time}|{VERSION}".encode()
    ).hexdigest()[:16].upper()

    fill_objects = []
    for index, target in enumerate(targets, start=1):
        fill_id = "FILL-" + hashlib.sha256(
            f"{source['fill_simulation_authorization_id']}|{target['paper_order_id']}|{target['offline_submission_id']}|{VERSION}".encode()
        ).hexdigest()[:16].upper()
        fill = {
            "fill_index": index,
            "fill_id": fill_id,
            "fill_simulation_execution_id": execution_id,
            "fill_simulation_authorization_id": source["fill_simulation_authorization_id"],
            "offline_submission_id": target["offline_submission_id"],
            "paper_order_id": target["paper_order_id"],
            "order_intent_id": target["order_intent_id"],
            "authorization_id": target["authorization_id"],
            "symbol": target["symbol"],
            "side": target["side"],
            "filled_quantity": target["quantity"],
            "fill_price": target["reference_price"],
            "notional_value": round(float(target["reference_price"]) * target["quantity"], 10),
            "currency": "USD",
            "fill_type": "OFFLINE_PAPER_REFERENCE_FILL",
            "fill_state": "FILLED_OFFLINE_OBJECT_ONLY",
            "fill_price_policy": "REFERENCE_PRICE_ONLY",
            "fill_quantity_policy": "FULL_QUANTITY_ONLY",
            "simulated_at": execution_time,
            "offline_only": True,
            "broker_connected": False,
            "broker_routed": False,
            "external_submission": False,
            "network_used": False,
            "position_updated": False,
            "cash_updated": False,
            "portfolio_updated": False,
            "approved_for_live": False,
        }
        fill["fill_object_sha256"] = sha256_of(fill)
        fill_objects.append(fill)

    consumed_token = copy.deepcopy(source["fill_simulation_authorization_token"])
    consumed_token.update({
        "consumed": True,
        "consumed_at": execution_time,
        "token_state": "CONSUMED_BY_OFFLINE_FILL_SIMULATION",
        "consumed_by_execution_id": execution_id,
    })

    checks = [
        {"check_index": 1, "check": "AUTHORIZATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "AUTHORIZED_TARGETS_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "SINGLE_USE_TOKEN_VALID", "state": "PASS"},
        {"check_index": 4, "check": "TOKEN_NOT_EXPIRED", "state": "PASS"},
        {"check_index": 5, "check": "REFERENCE_PRICE_LOCK", "state": "LOCKED"},
        {"check_index": 6, "check": "FULL_QUANTITY_LOCK", "state": "LOCKED"},
        {"check_index": 7, "check": "FILL_OBJECTS_CREATED_OFFLINE", "state": "PASS"},
        {"check_index": 8, "check": "POSITION_UPDATE_BLOCKED", "state": "ENFORCED"},
        {"check_index": 9, "check": "CASH_UPDATE_BLOCKED", "state": "ENFORCED"},
        {"check_index": 10, "check": "PORTFOLIO_UPDATE_BLOCKED", "state": "ENFORCED"},
        {"check_index": 11, "check": "BROKER_AND_NETWORK_BLOCKED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "FILL_SIMULATION_AUTHORIZATION_VERIFIED", "state": "PASS", "execution_id": execution_id},
        {"ledger_index": 2, "event": "SINGLE_USE_TOKEN_CONSUMED", "state": "CONSUMED", "execution_id": execution_id},
        {"ledger_index": 3, "event": "REFERENCE_PRICE_AND_FULL_QUANTITY_APPLIED", "state": "LOCKED", "execution_id": execution_id},
        {"ledger_index": 4, "event": "OFFLINE_FILL_OBJECTS_CREATED", "state": "CREATED", "execution_id": execution_id},
        {"ledger_index": 5, "event": "POSITION_CASH_PORTFOLIO_UPDATES_SKIPPED", "state": "ENFORCED", "execution_id": execution_id},
        {"ledger_index": 6, "event": "OFFLINE_FILL_SIMULATION_EXECUTION_COMPLETED", "state": "EXECUTED_OBJECT_ONLY", "execution_id": execution_id},
    ]

    output = {
        "status": "PASS",
        "decision": "offline_paper_fill_simulation_executed_object_only",
        "fill_simulation_execution_id": execution_id,
        "fill_simulation_authorization_id": source["fill_simulation_authorization_id"],
        "execution_scope": "OFFLINE_PAPER_FILL_OBJECT_CREATION_ONLY",
        "execution_state": "EXECUTED_FILL_OBJECT_ONLY",
        "fill_simulation_authorized": True,
        "fill_simulation_executed": True,
        "fill_object_creation_executed": True,
        "fill_object_count": len(fill_objects),
        "fill_objects": fill_objects,
        "fill_objects_sha256": sha256_of(fill_objects),
        "consumed_authorization_token": consumed_token,
        "consumed_authorization_token_sha256": sha256_of(consumed_token),
        "execution_checks": checks,
        "execution_checks_sha256": sha256_of(checks),
        "execution_ledger": ledger,
        "execution_ledger_sha256": sha256_of(ledger),
        "execution_gate": {
            "fill_object_creation_completed": True,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AB",
        },
        "source_fill_simulation_authorization_sha256": source["offline_paper_fill_simulation_authorization_sha256"],
        "source_authorized_targets_sha256": source["authorized_fill_simulation_targets_sha256"],
        "source_authorization_token_sha256": source["fill_simulation_authorization_token"]["token_sha256"],
        "submission_validation_id": source["submission_validation_id"],
        "submission_execution_id": source["submission_execution_id"],
        "authorization_id": source["authorization_id"],
        "validation_id": source["validation_id"],
        "execution_id": source["execution_id"],
        "authorization_source_id": source["authorization_source_id"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "executed_at": execution_time,
        "fill_objects_created": len(fill_objects),
        "fills_created": len(fill_objects),
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
    output["offline_paper_fill_simulation_execution_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_fill_simulation_execution_v75_2aa.json": output,
        "offline_paper_fill_objects_v75_2aa.json": {
            "fill_simulation_execution_id": output["fill_simulation_execution_id"],
            "fill_object_count": output["fill_object_count"],
            "fill_objects": output["fill_objects"],
            "fill_objects_sha256": output["fill_objects_sha256"],
        },
        "offline_paper_consumed_fill_simulation_token_v75_2aa.json": output["consumed_authorization_token"],
        "offline_paper_fill_simulation_execution_checks_v75_2aa.json": {
            "fill_simulation_execution_id": output["fill_simulation_execution_id"],
            "execution_checks": output["execution_checks"],
            "execution_checks_sha256": output["execution_checks_sha256"],
        },
        "offline_paper_fill_simulation_execution_ledger_v75_2aa.json": {
            "fill_simulation_execution_id": output["fill_simulation_execution_id"],
            "execution_ledger": output["execution_ledger"],
            "execution_ledger_sha256": output["execution_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_fill_simulation_execution_v75_2aa.sha256").write_text(
        output["offline_paper_fill_simulation_execution_sha256"] + "\n", encoding="utf-8"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--executed-at")
    args = parser.parse_args(argv)
    try:
        output = build_execution(read_json(Path(args.input)), read_json(Path(args.config)), args.executed_at)
        write_outputs(output, Path(args.output_dir))
        print(json.dumps({
            "status": output["status"],
            "decision": output["decision"],
            "fill_simulation_execution_id": output["fill_simulation_execution_id"],
            "execution_state": output["execution_state"],
            "fill_object_count": output["fill_object_count"],
            "first_fill_object": output["fill_objects"][0],
            "token_state": output["consumed_authorization_token"]["token_state"],
            "positions_updated": 0,
            "cash_updates_created": 0,
            "portfolio_updates_created": 0,
            "external_orders_submitted": 0,
            "broker_routes_created": 0,
            "network_used": False,
            "approved_for_live": False,
            "offline_paper_fill_simulation_execution_sha256": output["offline_paper_fill_simulation_execution_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (FillSimulationExecutionError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_fill_simulation_execution_failed",
            "error": str(exc),
            "fill_objects_created": 0,
            "fills_created": 0,
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
