from __future__ import annotations

import argparse
import copy
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2Q"
SCHEMA_VERSION = "v75.2q.offline_paper_order_intent_authorization.1"
SOURCE_SCHEMA = "v75.2p.offline_paper_signal_output_validation.1"


class OrderIntentAuthorizationError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OrderIntentAuthorizationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OrderIntentAuthorizationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OrderIntentAuthorizationError("top-level JSON must be an object")
    return value


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise OrderIntentAuthorizationError(
            f"{field} must be a non-empty ISO-8601 string"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OrderIntentAuthorizationError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise OrderIntentAuthorizationError(f"{field} must include timezone")
    return parsed


def validate_config(config: Dict[str, Any]) -> int:
    ttl = config.get("authorization_ttl_seconds")
    if isinstance(ttl, bool) or not isinstance(ttl, int) or not (60 <= ttl <= 3600):
        raise OrderIntentAuthorizationError(
            "authorization_ttl_seconds must be between 60 and 3600"
        )
    if config.get("authorization_scope") != "OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY":
        raise OrderIntentAuthorizationError("authorization_scope is invalid")
    if config.get("allowed_signal_actions") != ["BUY", "SELL", "HOLD"]:
        raise OrderIntentAuthorizationError("allowed_signal_actions is invalid")
    for key in (
        "require_single_use_token",
        "require_source_integrity",
        "require_validated_signals",
        "require_signal_identity_lock",
        "require_zero_orders",
        "require_safety_lock",
    ):
        if config.get(key) is not True:
            raise OrderIntentAuthorizationError(f"{key} must be true")
    for key in (
        "order_intent_creation_allowed",
        "order_generation_allowed",
        "fill_simulation_allowed",
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise OrderIntentAuthorizationError(f"{key} must be false")
    return ttl


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise OrderIntentAuthorizationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise OrderIntentAuthorizationError("unsupported source schema")
    if source.get("validation_state") != "READY_FOR_ORDER_INTENT_AUTHORIZATION":
        raise OrderIntentAuthorizationError(
            "source is not ready for order intent authorization"
        )

    observed = source.get("offline_paper_signal_output_validation_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise OrderIntentAuthorizationError("source validation SHA256 is invalid")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_signal_output_validation_sha256", None)
    if sha256_of(clone) != observed:
        raise OrderIntentAuthorizationError("source validation integrity failed")

    checks = source.get("validation_checks")
    ledger = source.get("validation_ledger")
    if source.get("validation_checks_sha256") != sha256_of(checks):
        raise OrderIntentAuthorizationError("validation checks integrity failed")
    if source.get("validation_ledger_sha256") != sha256_of(ledger):
        raise OrderIntentAuthorizationError("validation ledger integrity failed")

    gate = source.get("validation_gate")
    expected = {
        "signal_output_validated": True,
        "order_intent_authorization_allowed": True,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise OrderIntentAuthorizationError("validation_gate is required")
    for key, value in expected.items():
        if gate.get(key) != value:
            raise OrderIntentAuthorizationError(f"validation_gate {key} is invalid")

    signals = source.get("validated_signals")
    summary = source.get("validated_signal_summary")
    if not isinstance(signals, list) or not signals:
        raise OrderIntentAuthorizationError("validated_signals are required")
    if not isinstance(summary, dict):
        raise OrderIntentAuthorizationError("validated_signal_summary is required")
    if summary.get("signal_count") != len(signals):
        raise OrderIntentAuthorizationError("validated signal count mismatch")

    counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
    seen_ids = set()
    for signal in signals:
        if not isinstance(signal, dict):
            raise OrderIntentAuthorizationError("validated signal must be an object")
        action = signal.get("action")
        if action not in counts:
            raise OrderIntentAuthorizationError("validated signal action is invalid")
        signal_id = signal.get("signal_id")
        if not isinstance(signal_id, str) or not signal_id.startswith("SIG-"):
            raise OrderIntentAuthorizationError("validated signal_id is invalid")
        if signal_id in seen_ids:
            raise OrderIntentAuthorizationError("duplicate validated signal_id")
        seen_ids.add(signal_id)
        counts[action] += 1
        if signal.get("order_created") is not False:
            raise OrderIntentAuthorizationError("order_created must be false")
        if signal.get("order_submitted") is not False:
            raise OrderIntentAuthorizationError("order_submitted must be false")

    if summary.get("buy_count") != counts["BUY"]:
        raise OrderIntentAuthorizationError("buy_count mismatch")
    if summary.get("sell_count") != counts["SELL"]:
        raise OrderIntentAuthorizationError("sell_count mismatch")
    if summary.get("hold_count") != counts["HOLD"]:
        raise OrderIntentAuthorizationError("hold_count mismatch")

    for key in (
        "order_generation_allowed",
        "fill_simulation_allowed",
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
    ):
        if source.get(key) is not False:
            raise OrderIntentAuthorizationError(f"{key} must be false")
    if source.get("orders_created") != 0 or source.get("orders_submitted") != 0:
        raise OrderIntentAuthorizationError("order side effects detected")
    if source.get("approved_for_live") is not False:
        raise OrderIntentAuthorizationError("approved_for_live must be false")
    if source.get("network_used") is not False:
        raise OrderIntentAuthorizationError("network_used must be false")

    lock = source.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise OrderIntentAuthorizationError("safety lock must be ENFORCED")
    for key in (
        "broker_connected",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_orders_enabled",
        "live_trading_approval_allowed",
        "network_enabled",
    ):
        if lock.get(key) is not False:
            raise OrderIntentAuthorizationError(f"safety_lock {key} must be false")


def authorization_id(validation_id: str, issued_at: str) -> str:
    material = f"{validation_id}|{issued_at}|{VERSION}"
    return "OIA-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def build_token(
    authorization_id_value: str,
    validation_id: str,
    issued_at: str,
    expires_at: str,
    signal_ids: List[str],
    nonce: Optional[str],
) -> Dict[str, Any]:
    token_material = {
        "authorization_id": authorization_id_value,
        "validation_id": validation_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce or secrets.token_hex(16),
        "scope": "OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY",
        "authorized_signal_ids": signal_ids,
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

    issued = (
        datetime.now(timezone.utc).replace(microsecond=0)
        if issued_at is None
        else parse_timestamp(issued_at, "issued_at")
    )
    expires = issued + timedelta(seconds=ttl)
    issued_value = issued.isoformat()
    expires_value = expires.isoformat()
    aid = authorization_id(source["validation_id"], issued_value)
    signal_ids = [signal["signal_id"] for signal in source["validated_signals"]]
    token = build_token(
        aid,
        source["validation_id"],
        issued_value,
        expires_value,
        signal_ids,
        nonce,
    )

    authorized_signal_manifest = [
        {
            "signal_id": signal["signal_id"],
            "symbol": signal["symbol"],
            "action": signal["action"],
            "as_of": signal["as_of"],
            "latest_price": signal["latest_price"],
            "order_intent_creation_authorized": True,
            "order_created": False,
            "order_submitted": False,
        }
        for signal in source["validated_signals"]
    ]

    checks = [
        {"check_index": 1, "check": "SIGNAL_OUTPUT_VALIDATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "VALIDATED_SIGNAL_MANIFEST", "state": "PASS"},
        {"check_index": 3, "check": "SIGNAL_IDENTITY_LOCK", "state": "LOCKED"},
        {"check_index": 4, "check": "ORDER_INTENT_NOT_CREATED", "state": "PASS"},
        {"check_index": 5, "check": "ORDER_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 6, "check": "FILL_SIMULATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 7, "check": "ZERO_ORDER_SIDE_EFFECTS", "state": "PASS"},
        {"check_index": 8, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 9, "check": "BROKER_DISCONNECTED", "state": "PASS"},
        {"check_index": 10, "check": "SINGLE_USE_TOKEN_POLICY", "state": "ENFORCED"},
        {"check_index": 11, "check": "AUTHORIZATION_SCOPE_LIMIT", "state": "ENFORCED"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "SIGNAL_OUTPUT_VALIDATION_VERIFIED", "state": "PASS", "authorization_id": aid},
        {"ledger_index": 2, "event": "VALIDATED_SIGNAL_IDENTITIES_LOCKED", "state": "LOCKED", "authorization_id": aid},
        {"ledger_index": 3, "event": "ORDER_INTENT_SCOPE_AUTHORIZED", "state": "AUTHORIZED", "authorization_id": aid},
        {"ledger_index": 4, "event": "SINGLE_USE_TOKEN_ISSUED", "state": "ISSUED_NOT_CONSUMED", "authorization_id": aid},
        {"ledger_index": 5, "event": "SAFETY_LOCKS_RECONFIRMED", "state": "ENFORCED", "authorization_id": aid},
        {"ledger_index": 6, "event": "ORDER_INTENT_AUTHORIZATION_COMPLETED", "state": "AUTHORIZED_NOT_EXECUTED", "authorization_id": aid},
    ]

    result = {
        "status": "PASS",
        "decision": "offline_paper_order_intent_authorized",
        "authorization_id": aid,
        "authorization_scope": "OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY",
        "authorization_state": "AUTHORIZED_NOT_EXECUTED",
        "order_intent_authorized": True,
        "order_intent_created": False,
        "token_consumed": False,
        "authorization_token": token,
        "authorization_token_sha256": sha256_of(token),
        "authorized_signal_manifest": authorized_signal_manifest,
        "authorized_signal_manifest_sha256": sha256_of(authorized_signal_manifest),
        "authorization_checks": checks,
        "authorization_checks_sha256": sha256_of(checks),
        "authorization_ledger": ledger,
        "authorization_ledger_sha256": sha256_of(ledger),
        "source_signal_output_validation_sha256":
            source["offline_paper_signal_output_validation_sha256"],
        "source_signal_generation_execution_sha256":
            source["source_signal_generation_execution_sha256"],
        "source_signal_output_package_sha256":
            source["source_signal_output_package_sha256"],
        "validation_id": source["validation_id"],
        "signal_execution_id": source["signal_execution_id"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "authorization_gate": {
            "order_intent_authorized": True,
            "order_intent_creation_execution_allowed": True,
            "order_intent_creation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2R",
        },
        "order_intents_created": 0,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_created": 0,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(source["safety_lock"]),
        "issued_at": issued_value,
        "expires_at": expires_value,
        "authorization_ttl_seconds": ttl,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_order_intent_authorization_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_order_intent_authorization_v75_2q.json": result,
        "offline_paper_order_intent_authorization_token_v75_2q.json":
            result["authorization_token"],
        "offline_paper_order_intent_authorized_signals_v75_2q.json": {
            "authorization_id": result["authorization_id"],
            "authorized_signal_manifest": result["authorized_signal_manifest"],
            "authorized_signal_manifest_sha256":
                result["authorized_signal_manifest_sha256"],
        },
        "offline_paper_order_intent_authorization_checks_v75_2q.json": {
            "authorization_id": result["authorization_id"],
            "authorization_checks": result["authorization_checks"],
            "authorization_checks_sha256": result["authorization_checks_sha256"],
        },
        "offline_paper_order_intent_authorization_ledger_v75_2q.json": {
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
    (output_dir / "offline_paper_order_intent_authorization_v75_2q.sha256").write_text(
        result["offline_paper_order_intent_authorization_sha256"] + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.2Q Offline Paper Order Intent Authorization"
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
            "signal_execution_id": result["signal_execution_id"],
            "authorized_signal_count": len(result["authorized_signal_manifest"]),
            "authorized_signals": [
                {
                    "signal_id": signal["signal_id"],
                    "symbol": signal["symbol"],
                    "action": signal["action"],
                }
                for signal in result["authorized_signal_manifest"]
            ],
            "order_intent_authorized": result["order_intent_authorized"],
            "order_intent_created": result["order_intent_created"],
            "order_intent_creation_execution_allowed":
                result["authorization_gate"][
                    "order_intent_creation_execution_allowed"
                ],
            "order_intent_creation_allowed":
                result["authorization_gate"]["order_intent_creation_allowed"],
            "token_state": result["authorization_token"]["token_state"],
            "token_consumed": result["token_consumed"],
            "expires_at": result["expires_at"],
            "order_generation_allowed": result["order_generation_allowed"],
            "orders_created": result["orders_created"],
            "orders_submitted": result["orders_submitted"],
            "network_allowed": result["network_allowed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "offline_paper_order_intent_authorization_sha256":
                result["offline_paper_order_intent_authorization_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OrderIntentAuthorizationError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_order_intent_authorization_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "order_intents_created": 0,
            "orders_created": 0,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
