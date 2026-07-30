from __future__ import annotations

import argparse
import copy
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2N"
SCHEMA_VERSION = "v75.2n.offline_paper_signal_generation_authorization.1"
SOURCE_SCHEMA = "v75.2m.offline_paper_signal_input_validation.1"


class SignalGenerationAuthorizationError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SignalGenerationAuthorizationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SignalGenerationAuthorizationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SignalGenerationAuthorizationError("top-level JSON must be an object")
    return value


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SignalGenerationAuthorizationError(
            f"{field} must be a non-empty ISO-8601 string"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SignalGenerationAuthorizationError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SignalGenerationAuthorizationError(f"{field} must include timezone")
    return parsed


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise SignalGenerationAuthorizationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise SignalGenerationAuthorizationError("unsupported source schema")
    if source.get("validation_state") != "READY_FOR_SIGNAL_GENERATION_AUTHORIZATION":
        raise SignalGenerationAuthorizationError(
            "source is not ready for signal generation authorization"
        )

    observed = source.get("offline_paper_signal_input_validation_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise SignalGenerationAuthorizationError("source validation SHA256 is invalid")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_signal_input_validation_sha256", None)
    if sha256_of(clone) != observed:
        raise SignalGenerationAuthorizationError("source validation integrity failed")

    evidence = source.get("validation_evidence")
    checks = source.get("validation_checks")
    ledger = source.get("validation_ledger")
    if source.get("validation_evidence_sha256") != sha256_of(evidence):
        raise SignalGenerationAuthorizationError("validation evidence integrity failed")
    if source.get("validation_checks_sha256") != sha256_of(checks):
        raise SignalGenerationAuthorizationError("validation checks integrity failed")
    if source.get("validation_ledger_sha256") != sha256_of(ledger):
        raise SignalGenerationAuthorizationError("validation ledger integrity failed")

    gate = source.get("validation_gate")
    expected = {
        "signal_input_validated": True,
        "signal_generation_authorization_allowed": True,
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise SignalGenerationAuthorizationError("validation_gate is required")
    for key, expected_value in expected.items():
        if gate.get(key) != expected_value:
            raise SignalGenerationAuthorizationError(
                f"validation_gate {key} is invalid"
            )

    if not isinstance(evidence, dict):
        raise SignalGenerationAuthorizationError("validation_evidence is required")
    market = evidence.get("market_summary")
    strategy = evidence.get("strategy_summary")
    if not isinstance(market, dict) or not isinstance(strategy, dict):
        raise SignalGenerationAuthorizationError(
            "validated market and strategy summaries are required"
        )
    if market.get("immutable") is not True:
        raise SignalGenerationAuthorizationError("market summary must be immutable")
    if market.get("network_source") is not False:
        raise SignalGenerationAuthorizationError("network source must be false")
    if market.get("strict_time_order") is not True:
        raise SignalGenerationAuthorizationError("strict time order must be true")
    if market.get("duplicate_symbol_timestamps") != 0:
        raise SignalGenerationAuthorizationError("duplicate bars must be absent")
    if strategy.get("immutable") is not True:
        raise SignalGenerationAuthorizationError("strategy summary must be immutable")
    if strategy.get("history_sufficient") is not True:
        raise SignalGenerationAuthorizationError("history must be sufficient")
    if strategy.get("window_consistency") is not True:
        raise SignalGenerationAuthorizationError("strategy windows must be consistent")

    for key in (
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
    ):
        if source.get(key) is not False:
            raise SignalGenerationAuthorizationError(f"{key} must be false")
    if source.get("orders_submitted") != 0:
        raise SignalGenerationAuthorizationError("orders_submitted must be zero")
    if source.get("approved_for_live") is not False:
        raise SignalGenerationAuthorizationError("approved_for_live must be false")
    if source.get("network_used") is not False:
        raise SignalGenerationAuthorizationError("network_used must be false")

    lock = source.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise SignalGenerationAuthorizationError("safety lock must be ENFORCED")
    for key in (
        "broker_connected",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_orders_enabled",
        "live_trading_approval_allowed",
        "network_enabled",
    ):
        if lock.get(key) is not False:
            raise SignalGenerationAuthorizationError(
                f"safety_lock {key} must be false"
            )


def validate_config(config: Dict[str, Any]) -> int:
    ttl = config.get("authorization_ttl_seconds")
    if isinstance(ttl, bool) or not isinstance(ttl, int) or not (60 <= ttl <= 3600):
        raise SignalGenerationAuthorizationError(
            "authorization_ttl_seconds must be between 60 and 3600"
        )
    if config.get("authorization_scope") != "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY":
        raise SignalGenerationAuthorizationError("authorization_scope is invalid")
    for key in (
        "require_single_use_token",
        "require_source_integrity",
        "require_validated_inputs",
        "require_safety_lock",
        "require_zero_orders",
    ):
        if config.get(key) is not True:
            raise SignalGenerationAuthorizationError(f"{key} must be true")
    for key in (
        "signal_generation_allowed",
        "order_generation_allowed",
        "fill_simulation_allowed",
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise SignalGenerationAuthorizationError(f"{key} must be false")
    return ttl


def authorization_id(validation_id: str, issued_at: str) -> str:
    material = f"{validation_id}|{issued_at}|{VERSION}"
    return "SGA-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def build_token(
    authorization_id_value: str,
    validation_id: str,
    issued_at: str,
    expires_at: str,
    nonce: Optional[str],
) -> Dict[str, Any]:
    token_nonce = nonce or secrets.token_hex(16)
    token_material = {
        "authorization_id": authorization_id_value,
        "validation_id": validation_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": token_nonce,
        "scope": "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
    }
    return {
        **token_material,
        "token_sha256": sha256_of(token_material),
        "single_use": True,
        "consumed": False,
        "consumed_at": None,
        "token_state": "ISSUED_NOT_CONSUMED",
    }


def build_authorization(
    source: Dict[str, Any],
    config: Dict[str, Any],
    issued_at: Optional[str] = None,
    nonce: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    ttl = validate_config(config)

    if issued_at is None:
        issued = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        issued = parse_timestamp(issued_at, "issued_at")
    expires = issued + timedelta(seconds=ttl)
    issued_at_value = issued.isoformat()
    expires_at_value = expires.isoformat()
    aid = authorization_id(source["validation_id"], issued_at_value)
    token = build_token(
        aid,
        source["validation_id"],
        issued_at_value,
        expires_at_value,
        nonce,
    )

    checks = [
        {"check_index": 1, "check": "SIGNAL_INPUT_VALIDATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "VALIDATION_EVIDENCE_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "VALIDATED_INPUT_GATE", "state": "PASS"},
        {"check_index": 4, "check": "MARKET_DATA_IMMUTABILITY", "state": "LOCKED"},
        {"check_index": 5, "check": "STRATEGY_INPUT_IMMUTABILITY", "state": "LOCKED"},
        {"check_index": 6, "check": "SIGNAL_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 7, "check": "ORDER_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 8, "check": "ZERO_ORDER_SIDE_EFFECTS", "state": "PASS"},
        {"check_index": 9, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 10, "check": "BROKER_DISCONNECTED", "state": "PASS"},
        {"check_index": 11, "check": "SINGLE_USE_TOKEN_POLICY", "state": "ENFORCED"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "SIGNAL_INPUT_VALIDATION_VERIFIED", "state": "PASS", "authorization_id": aid},
        {"ledger_index": 2, "event": "VALIDATED_INPUT_SCOPE_LOCKED", "state": "LOCKED", "authorization_id": aid},
        {"ledger_index": 3, "event": "SIGNAL_GENERATION_SCOPE_AUTHORIZED", "state": "AUTHORIZED", "authorization_id": aid},
        {"ledger_index": 4, "event": "SINGLE_USE_TOKEN_ISSUED", "state": "ISSUED_NOT_CONSUMED", "authorization_id": aid},
        {"ledger_index": 5, "event": "SAFETY_LOCKS_RECONFIRMED", "state": "ENFORCED", "authorization_id": aid},
        {"ledger_index": 6, "event": "SIGNAL_GENERATION_AUTHORIZATION_COMPLETED", "state": "AUTHORIZED_NOT_EXECUTED", "authorization_id": aid},
    ]

    result = {
        "status": "PASS",
        "decision": "offline_paper_signal_generation_authorized",
        "authorization_id": aid,
        "authorization_scope": "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
        "authorization_state": "AUTHORIZED_NOT_EXECUTED",
        "signal_generation_authorized": True,
        "signal_generation_executed": False,
        "token_consumed": False,
        "authorization_token": token,
        "authorization_token_sha256": sha256_of(token),
        "authorization_checks": checks,
        "authorization_checks_sha256": sha256_of(checks),
        "authorization_ledger": ledger,
        "authorization_ledger_sha256": sha256_of(ledger),
        "source_signal_input_validation_sha256":
            source["offline_paper_signal_input_validation_sha256"],
        "source_signal_input_package_sha256":
            source["source_signal_input_package_sha256"],
        "validation_id": source["validation_id"],
        "preparation_id": source["preparation_id"],
        "certificate_id": source["certificate_id"],
        "execution_id": source["execution_id"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "authorization_gate": {
            "signal_generation_authorized": True,
            "signal_generation_execution_allowed": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2O",
        },
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(source["safety_lock"]),
        "issued_at": issued_at_value,
        "expires_at": expires_at_value,
        "authorization_ttl_seconds": ttl,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_signal_generation_authorization_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_signal_generation_authorization_v75_2n.json": result,
        "offline_paper_signal_generation_authorization_token_v75_2n.json":
            result["authorization_token"],
        "offline_paper_signal_generation_authorization_checks_v75_2n.json": {
            "authorization_id": result["authorization_id"],
            "authorization_checks": result["authorization_checks"],
            "authorization_checks_sha256": result["authorization_checks_sha256"],
        },
        "offline_paper_signal_generation_authorization_ledger_v75_2n.json": {
            "authorization_id": result["authorization_id"],
            "authorization_ledger": result["authorization_ledger"],
            "authorization_ledger_sha256": result["authorization_ledger_sha256"],
        },
    }
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / "offline_paper_signal_generation_authorization_v75_2n.sha256").write_text(
        result["offline_paper_signal_generation_authorization_sha256"] + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.2N Offline Paper Signal Generation Authorization"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--issued-at")
    parser.add_argument("--nonce")
    args = parser.parse_args(argv)
    try:
        result = build_authorization(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.issued_at,
            args.nonce,
        )
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "authorization_id": result["authorization_id"],
            "authorization_scope": result["authorization_scope"],
            "authorization_state": result["authorization_state"],
            "validation_id": result["validation_id"],
            "session_id": result["session_id"],
            "cycle_id": result["cycle_id"],
            "cycle_sequence": result["cycle_sequence"],
            "signal_generation_authorized": result["signal_generation_authorized"],
            "signal_generation_executed": result["signal_generation_executed"],
            "signal_generation_execution_allowed":
                result["authorization_gate"]["signal_generation_execution_allowed"],
            "signal_generation_allowed":
                result["authorization_gate"]["signal_generation_allowed"],
            "order_generation_allowed":
                result["authorization_gate"]["order_generation_allowed"],
            "token_state": result["authorization_token"]["token_state"],
            "token_consumed": result["token_consumed"],
            "expires_at": result["expires_at"],
            "paper_orders_allowed": result["paper_orders_allowed"],
            "live_orders_allowed": result["live_orders_allowed"],
            "network_allowed": result["network_allowed"],
            "orders_submitted": result["orders_submitted"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "offline_paper_signal_generation_authorization_sha256":
                result["offline_paper_signal_generation_authorization_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (SignalGenerationAuthorizationError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_signal_generation_authorization_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
