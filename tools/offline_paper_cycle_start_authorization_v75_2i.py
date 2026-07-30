from __future__ import annotations

import argparse
import copy
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2I"
SCHEMA_VERSION = "v75.2i.offline_paper_cycle_start_authorization.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2h.offline_paper_runtime_readiness_certificate.1"


class CycleAuthorizationError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CycleAuthorizationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CycleAuthorizationError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise CycleAuthorizationError("top-level JSON must be an object")
    return data


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise CycleAuthorizationError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise CycleAuthorizationError("unsupported source schema_version")
    if source.get("certificate_state") != "READY_FOR_OFFLINE_PAPER_CYCLE":
        raise CycleAuthorizationError("source certificate is not ready for an offline paper cycle")
    if source.get("approved_for_live") is not False:
        raise CycleAuthorizationError("approved_for_live must remain false")
    if source.get("network_used") is not False:
        raise CycleAuthorizationError("network_used must remain false")
    if source.get("orders_submitted") != 0:
        raise CycleAuthorizationError("orders_submitted must be zero")

    observed = source.get("offline_paper_runtime_readiness_certificate_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise CycleAuthorizationError("readiness certificate hash is invalid")
    copied = copy.deepcopy(source)
    copied.pop("offline_paper_runtime_readiness_certificate_sha256", None)
    if observed != sha256_of(copied):
        raise CycleAuthorizationError("readiness certificate integrity verification failed")

    checks = source.get("readiness_checks")
    if not isinstance(checks, list) or len(checks) < 1:
        raise CycleAuthorizationError("readiness checks are required")
    if source.get("readiness_checks_sha256") != sha256_of(checks):
        raise CycleAuthorizationError("readiness checks integrity failed")
    if [x.get("check_index") for x in checks] != list(range(1, len(checks) + 1)):
        raise CycleAuthorizationError("readiness check indexes must be sequential")

    ledger = source.get("readiness_ledger")
    if not isinstance(ledger, list) or len(ledger) < 1:
        raise CycleAuthorizationError("readiness ledger is required")
    if source.get("readiness_ledger_sha256") != sha256_of(ledger):
        raise CycleAuthorizationError("readiness ledger integrity failed")
    if [x.get("ledger_index") for x in ledger] != list(range(1, len(ledger) + 1)):
        raise CycleAuthorizationError("readiness ledger indexes must be sequential")

    snapshot = source.get("runtime_snapshot")
    if not isinstance(snapshot, dict):
        raise CycleAuthorizationError("runtime snapshot is required")
    if source.get("runtime_snapshot_sha256") != sha256_of(snapshot):
        raise CycleAuthorizationError("runtime snapshot integrity failed")
    if snapshot.get("mode") != "OFFLINE_PAPER" or snapshot.get("state") != "ACTIVE":
        raise CycleAuthorizationError("runtime must be active in OFFLINE_PAPER mode")
    if snapshot.get("session_id") != source.get("session_id"):
        raise CycleAuthorizationError("runtime snapshot session_id mismatch")
    if snapshot.get("activation_id") != source.get("activation_id"):
        raise CycleAuthorizationError("runtime snapshot activation_id mismatch")
    if snapshot.get("champion_candidate_id") != source.get("champion_candidate_id"):
        raise CycleAuthorizationError("runtime snapshot champion mismatch")
    if snapshot.get("order_queue_size") != 0:
        raise CycleAuthorizationError("order queue must be empty")
    if snapshot.get("orders_submitted") != 0:
        raise CycleAuthorizationError("runtime submitted orders must be zero")
    if snapshot.get("positions_mutated") is not False:
        raise CycleAuthorizationError("positions must remain unmutated")
    for key in ("broker_connected", "network_enabled", "live_orders_enabled"):
        if snapshot.get(key) is not False:
            raise CycleAuthorizationError(f"runtime snapshot {key} must be false")

    gate = source.get("readiness_gate")
    expected_gate = {
        "offline_paper_runtime_ready": True,
        "offline_paper_cycle_allowed": True,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "operator_cycle_start_required": True,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise CycleAuthorizationError("readiness gate is required")
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise CycleAuthorizationError(f"readiness_gate {key} is invalid")

    lock = source.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise CycleAuthorizationError("safety lock must be ENFORCED")
    for key in (
        "broker_connected",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_orders_enabled",
        "live_trading_approval_allowed",
        "network_enabled",
    ):
        if lock.get(key) is not False:
            raise CycleAuthorizationError(f"safety_lock {key} must be false")


def validate_config(config: Dict[str, Any]) -> None:
    ttl = config.get("authorization_token_ttl_seconds")
    if not isinstance(ttl, int) or ttl < 60 or ttl > 86400:
        raise CycleAuthorizationError("authorization_token_ttl_seconds must be between 60 and 86400")
    for key in (
        "require_operator_cycle_start",
        "require_single_use_token",
        "require_zero_orders_before_start",
        "require_empty_order_queue",
        "require_unmutated_positions",
    ):
        if config.get(key) is not True:
            raise CycleAuthorizationError(f"{key} must be true")
    for key in (
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise CycleAuthorizationError(f"{key} must be false")


def authorization_id(certificate_id: str, issued_at: str) -> str:
    raw = f"{certificate_id}|{issued_at}|{VERSION}"
    return "PCA-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def build_authorization(
    source: Dict[str, Any],
    config: Dict[str, Any],
    issued_at: Optional[str] = None,
    raw_token: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)
    now = datetime.now(timezone.utc).replace(microsecond=0) if issued_at is None else datetime.fromisoformat(issued_at)
    if now.tzinfo is None:
        raise CycleAuthorizationError("issued_at must include timezone")
    issued_at_value = now.isoformat()
    expires_at = (now + timedelta(seconds=config["authorization_token_ttl_seconds"])).isoformat()
    aid = authorization_id(source["certificate_id"], issued_at_value)
    token = raw_token or secrets.token_urlsafe(32)
    token_record = {
        "authorization_id": aid,
        "certificate_id": source["certificate_id"],
        "session_id": source["session_id"],
        "single_use": True,
        "consumed": False,
        "issued_at": issued_at_value,
        "expires_at": expires_at,
        "ttl_seconds": config["authorization_token_ttl_seconds"],
        "token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
    }

    checks = [
        {"check_index": 1, "check": "READINESS_CERTIFICATE_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "OFFLINE_RUNTIME_READY", "state": "PASS"},
        {"check_index": 3, "check": "ORDER_QUEUE_EMPTY", "state": "PASS"},
        {"check_index": 4, "check": "ORDERS_SUBMITTED_ZERO", "state": "PASS"},
        {"check_index": 5, "check": "POSITIONS_UNMUTATED", "state": "PASS"},
        {"check_index": 6, "check": "BROKER_DISCONNECTED", "state": "PASS"},
        {"check_index": 7, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 8, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
        {"check_index": 9, "check": "SINGLE_USE_CYCLE_TOKEN_ISSUED", "state": "ISSUED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "READINESS_CERTIFICATE_VERIFIED", "state": "PASS", "authorization_id": aid},
        {"ledger_index": 2, "event": "RUNTIME_BASELINE_VERIFIED", "state": "PASS", "authorization_id": aid},
        {"ledger_index": 3, "event": "SAFETY_LOCKS_RECONFIRMED", "state": "ENFORCED", "authorization_id": aid},
        {"ledger_index": 4, "event": "CYCLE_START_TOKEN_ISSUED", "state": "ISSUED", "authorization_id": aid},
        {"ledger_index": 5, "event": "OFFLINE_PAPER_CYCLE_START_AUTHORIZED", "state": "AUTHORIZED_NOT_STARTED", "authorization_id": aid},
    ]

    result = {
        "status": "PASS",
        "decision": "offline_paper_cycle_start_authorized",
        "authorization_id": aid,
        "authorization_state": "AUTHORIZED_NOT_STARTED",
        "authorization_scope": "OFFLINE_PAPER_CYCLE_START_ONLY",
        "certificate_id": source["certificate_id"],
        "activation_id": source["activation_id"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "cycle_sequence": 1,
        "cycle_start_authorized": True,
        "cycle_started": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "cycle_start_token": token_record,
        "authorization_checks": checks,
        "authorization_ledger": ledger,
        "authorization_checks_sha256": sha256_of(checks),
        "authorization_ledger_sha256": sha256_of(ledger),
        "cycle_start_token_sha256": sha256_of(token_record),
        "source_readiness_certificate_sha256": source["offline_paper_runtime_readiness_certificate_sha256"],
        "authorization_gate": {
            "cycle_start_authorized": True,
            "cycle_start_allowed": False,
            "cycle_started": False,
            "token_consumed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2J",
        },
        "safety_lock": {
            "broker_connected": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "live_orders_enabled": False,
            "live_trading_approval_allowed": False,
            "network_enabled": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "issued_at": issued_at_value,
        "expires_at": expires_at,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_cycle_start_authorization_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_cycle_start_authorization_v75_2i.json": result,
        "offline_paper_cycle_start_authorization_checks_v75_2i.json": {
            "authorization_id": result["authorization_id"],
            "authorization_checks": result["authorization_checks"],
            "authorization_checks_sha256": result["authorization_checks_sha256"],
        },
        "offline_paper_cycle_start_authorization_ledger_v75_2i.json": {
            "authorization_id": result["authorization_id"],
            "authorization_ledger": result["authorization_ledger"],
            "authorization_ledger_sha256": result["authorization_ledger_sha256"],
        },
        "offline_paper_cycle_start_token_v75_2i.json": result["cycle_start_token"],
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_cycle_start_authorization_v75_2i.sha256").write_text(
        result["offline_paper_cycle_start_authorization_sha256"] + "\n", encoding="utf-8"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2I Offline Paper Cycle Start Authorization")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_authorization(read_json(Path(args.input)), read_json(Path(args.config)))
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "authorization_id": result["authorization_id"],
            "authorization_state": result["authorization_state"],
            "authorization_scope": result["authorization_scope"],
            "certificate_id": result["certificate_id"],
            "session_id": result["session_id"],
            "cycle_sequence": result["cycle_sequence"],
            "cycle_start_authorized": result["cycle_start_authorized"],
            "cycle_started": result["cycle_started"],
            "paper_orders_allowed": result["paper_orders_allowed"],
            "live_orders_allowed": result["live_orders_allowed"],
            "network_allowed": result["network_allowed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "orders_submitted": result["orders_submitted"],
            "offline_paper_cycle_start_authorization_sha256":
                result["offline_paper_cycle_start_authorization_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (CycleAuthorizationError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_cycle_start_authorization_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
