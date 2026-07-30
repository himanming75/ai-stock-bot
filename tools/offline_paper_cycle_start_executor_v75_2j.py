from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2J"
SCHEMA_VERSION = "v75.2j.offline_paper_cycle_start_execution.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2i.offline_paper_cycle_start_authorization.1"


class CycleStartExecutionError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CycleStartExecutionError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CycleStartExecutionError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CycleStartExecutionError("top-level JSON must be an object")
    return value


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise CycleStartExecutionError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CycleStartExecutionError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CycleStartExecutionError(f"{field} must include timezone")
    return parsed


def validate_source(source: Dict[str, Any], executed_at: datetime) -> None:
    if source.get("status") != "PASS":
        raise CycleStartExecutionError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise CycleStartExecutionError("unsupported source schema_version")
    if source.get("authorization_state") != "AUTHORIZED_NOT_STARTED":
        raise CycleStartExecutionError("authorization must be AUTHORIZED_NOT_STARTED")
    if source.get("authorization_scope") != "OFFLINE_PAPER_CYCLE_START_ONLY":
        raise CycleStartExecutionError("authorization scope is invalid")
    if source.get("cycle_start_authorized") is not True:
        raise CycleStartExecutionError("cycle start is not authorized")
    if source.get("cycle_started") is not False:
        raise CycleStartExecutionError("cycle has already started")
    if source.get("cycle_sequence") != 1:
        raise CycleStartExecutionError("cycle_sequence must be 1")
    if source.get("approved_for_live") is not False:
        raise CycleStartExecutionError("approved_for_live must remain false")
    if source.get("network_used") is not False:
        raise CycleStartExecutionError("network_used must remain false")
    if source.get("orders_submitted") != 0:
        raise CycleStartExecutionError("orders_submitted must be zero")

    observed = source.get("offline_paper_cycle_start_authorization_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise CycleStartExecutionError("authorization SHA256 is invalid")
    copied = copy.deepcopy(source)
    copied.pop("offline_paper_cycle_start_authorization_sha256", None)
    if sha256_of(copied) != observed:
        raise CycleStartExecutionError("authorization integrity verification failed")

    checks = source.get("authorization_checks")
    if not isinstance(checks, list) or not checks:
        raise CycleStartExecutionError("authorization checks are required")
    if source.get("authorization_checks_sha256") != sha256_of(checks):
        raise CycleStartExecutionError("authorization checks integrity failed")
    if [x.get("check_index") for x in checks] != list(range(1, len(checks) + 1)):
        raise CycleStartExecutionError("authorization check indexes must be sequential")

    ledger = source.get("authorization_ledger")
    if not isinstance(ledger, list) or not ledger:
        raise CycleStartExecutionError("authorization ledger is required")
    if source.get("authorization_ledger_sha256") != sha256_of(ledger):
        raise CycleStartExecutionError("authorization ledger integrity failed")
    if [x.get("ledger_index") for x in ledger] != list(range(1, len(ledger) + 1)):
        raise CycleStartExecutionError("authorization ledger indexes must be sequential")

    token = source.get("cycle_start_token")
    if not isinstance(token, dict):
        raise CycleStartExecutionError("cycle start token is required")
    if source.get("cycle_start_token_sha256") != sha256_of(token):
        raise CycleStartExecutionError("cycle start token integrity failed")
    if token.get("single_use") is not True:
        raise CycleStartExecutionError("cycle start token must be single-use")
    if token.get("consumed") is not False:
        raise CycleStartExecutionError("cycle start token has already been consumed")
    if token.get("authorization_id") != source.get("authorization_id"):
        raise CycleStartExecutionError("token authorization_id mismatch")
    if token.get("certificate_id") != source.get("certificate_id"):
        raise CycleStartExecutionError("token certificate_id mismatch")
    if token.get("session_id") != source.get("session_id"):
        raise CycleStartExecutionError("token session_id mismatch")
    if not isinstance(token.get("token_sha256"), str) or len(token["token_sha256"]) != 64:
        raise CycleStartExecutionError("token_sha256 is invalid")

    issued_at = parse_timestamp(token.get("issued_at"), "cycle_start_token.issued_at")
    expires_at = parse_timestamp(token.get("expires_at"), "cycle_start_token.expires_at")
    if executed_at < issued_at:
        raise CycleStartExecutionError("execution time is before token issuance")
    if executed_at > expires_at:
        raise CycleStartExecutionError("cycle start token has expired")

    gate = source.get("authorization_gate")
    expected_gate = {
        "cycle_start_authorized": True,
        "cycle_start_allowed": False,
        "cycle_started": False,
        "token_consumed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise CycleStartExecutionError("authorization gate is required")
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise CycleStartExecutionError(f"authorization_gate {key} is invalid")

    for key in (
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
    ):
        if source.get(key) is not False:
            raise CycleStartExecutionError(f"{key} must be false")

    lock = source.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise CycleStartExecutionError("safety lock must be ENFORCED")
    for key in (
        "broker_connected",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_orders_enabled",
        "live_trading_approval_allowed",
        "network_enabled",
    ):
        if lock.get(key) is not False:
            raise CycleStartExecutionError(f"safety_lock {key} must be false")


def validate_config(config: Dict[str, Any]) -> None:
    required_true = (
        "consume_single_use_token",
        "require_authorized_not_started",
        "require_empty_order_queue",
        "require_zero_orders",
        "require_unmutated_positions",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise CycleStartExecutionError(f"{key} must be true")
    required_false = (
        "generate_signals_on_start",
        "generate_orders_on_start",
        "simulate_fills_on_start",
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    )
    for key in required_false:
        if config.get(key) is not False:
            raise CycleStartExecutionError(f"{key} must be false")


def execution_id(authorization_id: str, executed_at: str) -> str:
    material = f"{authorization_id}|{executed_at}|{VERSION}"
    return "PCS-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def build_execution(
    source: Dict[str, Any],
    config: Dict[str, Any],
    executed_at: Optional[str] = None,
) -> Dict[str, Any]:
    when = (
        datetime.now(timezone.utc).replace(microsecond=0)
        if executed_at is None
        else parse_timestamp(executed_at, "executed_at")
    )
    validate_source(source, when)
    validate_config(config)

    executed_at_value = when.isoformat()
    eid = execution_id(source["authorization_id"], executed_at_value)

    consumed_token = copy.deepcopy(source["cycle_start_token"])
    consumed_token["consumed"] = True
    consumed_token["consumed_at"] = executed_at_value
    consumed_token["consumed_by_execution_id"] = eid

    cycle_state = {
        "cycle_id": eid,
        "cycle_sequence": source["cycle_sequence"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "mode": "OFFLINE_PAPER",
        "state": "ACTIVE",
        "started_at": executed_at_value,
        "signal_generation_started": False,
        "order_generation_started": False,
        "fill_simulation_started": False,
        "order_queue": [],
        "orders_submitted": 0,
        "positions_mutated": False,
        "broker_connected": False,
        "network_enabled": False,
        "live_orders_enabled": False,
    }

    checks = [
        {"check_index": 1, "check": "CYCLE_START_AUTHORIZATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "AUTHORIZATION_NOT_PREVIOUSLY_USED", "state": "PASS"},
        {"check_index": 3, "check": "CYCLE_START_TOKEN_VALID", "state": "PASS"},
        {"check_index": 4, "check": "CYCLE_START_TOKEN_CONSUMED", "state": "CONSUMED"},
        {"check_index": 5, "check": "OFFLINE_CYCLE_STATE_CREATED", "state": "ACTIVE"},
        {"check_index": 6, "check": "ORDER_QUEUE_EMPTY", "state": "PASS"},
        {"check_index": 7, "check": "ORDERS_SUBMITTED_ZERO", "state": "PASS"},
        {"check_index": 8, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 9, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "CYCLE_START_AUTHORIZATION_VERIFIED", "state": "PASS", "execution_id": eid},
        {"ledger_index": 2, "event": "CYCLE_START_TOKEN_VERIFIED", "state": "PASS", "execution_id": eid},
        {"ledger_index": 3, "event": "CYCLE_START_TOKEN_CONSUMED", "state": "CONSUMED", "execution_id": eid},
        {"ledger_index": 4, "event": "OFFLINE_PAPER_CYCLE_STATE_CREATED", "state": "ACTIVE", "execution_id": eid},
        {"ledger_index": 5, "event": "OFFLINE_PAPER_CYCLE_STARTED", "state": "ACTIVE", "execution_id": eid},
    ]

    result = {
        "status": "PASS",
        "decision": "offline_paper_cycle_started",
        "execution_id": eid,
        "execution_state": "OFFLINE_PAPER_CYCLE_ACTIVE",
        "authorization_id": source["authorization_id"],
        "authorization_state": "CONSUMED",
        "authorization_scope": source["authorization_scope"],
        "certificate_id": source["certificate_id"],
        "activation_id": source["activation_id"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "cycle_id": eid,
        "cycle_sequence": source["cycle_sequence"],
        "cycle_start_authorized": True,
        "cycle_started": True,
        "cycle_state": cycle_state,
        "consumed_cycle_start_token": consumed_token,
        "execution_checks": checks,
        "execution_ledger": ledger,
        "cycle_state_sha256": sha256_of(cycle_state),
        "consumed_cycle_start_token_sha256": sha256_of(consumed_token),
        "execution_checks_sha256": sha256_of(checks),
        "execution_ledger_sha256": sha256_of(ledger),
        "source_cycle_start_authorization_sha256":
            source["offline_paper_cycle_start_authorization_sha256"],
        "execution_gate": {
            "cycle_active": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2K",
        },
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": {
            "broker_connected": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "live_orders_enabled": False,
            "live_trading_approval_allowed": False,
            "network_enabled": False,
            "lock_state": "ENFORCED",
        },
        "executed_at": executed_at_value,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_cycle_start_execution_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_cycle_start_execution_v75_2j.json": result,
        "offline_paper_cycle_start_execution_checks_v75_2j.json": {
            "execution_id": result["execution_id"],
            "execution_checks": result["execution_checks"],
            "execution_checks_sha256": result["execution_checks_sha256"],
        },
        "offline_paper_cycle_start_execution_ledger_v75_2j.json": {
            "execution_id": result["execution_id"],
            "execution_ledger": result["execution_ledger"],
            "execution_ledger_sha256": result["execution_ledger_sha256"],
        },
        "offline_paper_cycle_state_v75_2j.json": result["cycle_state"],
        "offline_paper_cycle_start_token_consumed_v75_2j.json":
            result["consumed_cycle_start_token"],
    }
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (output_dir / "offline_paper_cycle_start_execution_v75_2j.sha256").write_text(
        result["offline_paper_cycle_start_execution_sha256"] + "\n", encoding="utf-8"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2J Offline Paper Cycle Start Executor")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--executed-at")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_execution(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.executed_at,
        )
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "execution_id": result["execution_id"],
            "execution_state": result["execution_state"],
            "authorization_id": result["authorization_id"],
            "authorization_state": result["authorization_state"],
            "session_id": result["session_id"],
            "cycle_id": result["cycle_id"],
            "cycle_sequence": result["cycle_sequence"],
            "cycle_started": result["cycle_started"],
            "cycle_active": result["execution_gate"]["cycle_active"],
            "signal_generation_allowed": result["execution_gate"]["signal_generation_allowed"],
            "order_generation_allowed": result["execution_gate"]["order_generation_allowed"],
            "fill_simulation_allowed": result["execution_gate"]["fill_simulation_allowed"],
            "paper_orders_allowed": result["paper_orders_allowed"],
            "live_orders_allowed": result["live_orders_allowed"],
            "network_allowed": result["network_allowed"],
            "orders_submitted": result["orders_submitted"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "offline_paper_cycle_start_execution_sha256":
                result["offline_paper_cycle_start_execution_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (CycleStartExecutionError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_cycle_start_execution_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
