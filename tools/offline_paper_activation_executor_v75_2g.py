from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2G"
SCHEMA_VERSION = "v75.2g.offline_paper_activation.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2f.paper_activation_authorization.1"


class OfflinePaperActivationError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflinePaperActivationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OfflinePaperActivationError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise OfflinePaperActivationError("top-level JSON must be an object")
    return data


def parse_iso8601(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OfflinePaperActivationError(f"{label} must be an ISO8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OfflinePaperActivationError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise OfflinePaperActivationError(f"{label} must include timezone")
    return parsed.astimezone(timezone.utc)


def validate_source(source: Dict[str, Any], executed_at: datetime) -> None:
    if source.get("status") != "PASS":
        raise OfflinePaperActivationError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise OfflinePaperActivationError("unsupported source schema_version")
    if source.get("authorization_state") != "AUTHORIZED_NOT_ACTIVATED":
        raise OfflinePaperActivationError("authorization_state must be AUTHORIZED_NOT_ACTIVATED")
    if source.get("authorization_scope") != "OFFLINE_PAPER_ACTIVATION_ONLY":
        raise OfflinePaperActivationError("authorization scope must be offline paper only")
    if source.get("approved_for_live") is not False or source.get("network_used") is not False:
        raise OfflinePaperActivationError("live approval and network use must remain false")

    observed_hash = source.get("paper_activation_authorization_sha256")
    if not isinstance(observed_hash, str) or len(observed_hash) != 64:
        raise OfflinePaperActivationError("authorization hash is invalid")
    copied = copy.deepcopy(source)
    copied.pop("paper_activation_authorization_sha256", None)
    if observed_hash != sha256_of(copied):
        raise OfflinePaperActivationError("authorization integrity verification failed")

    checks = source.get("authorization_checks")
    if not isinstance(checks, list) or len(checks) < 1:
        raise OfflinePaperActivationError("authorization checks are required")
    if source.get("authorization_checks_sha256") != sha256_of(checks):
        raise OfflinePaperActivationError("authorization checks integrity failed")
    if [x.get("check_index") for x in checks] != list(range(1, len(checks) + 1)):
        raise OfflinePaperActivationError("authorization check indexes must be sequential")
    allowed_states = {"PASS", "ENFORCED", "NOT_EXECUTED"}
    if any(x.get("state") not in allowed_states for x in checks):
        raise OfflinePaperActivationError("authorization checks contain an invalid state")

    ledger = source.get("authorization_ledger")
    if not isinstance(ledger, list) or len(ledger) < 1:
        raise OfflinePaperActivationError("authorization ledger is required")
    if source.get("authorization_ledger_sha256") != sha256_of(ledger):
        raise OfflinePaperActivationError("authorization ledger integrity failed")
    if [x.get("ledger_index") for x in ledger] != list(range(1, len(ledger) + 1)):
        raise OfflinePaperActivationError("authorization ledger indexes must be sequential")

    gate = source.get("activation_gate")
    if not isinstance(gate, dict):
        raise OfflinePaperActivationError("activation gate is required")
    if gate.get("paper_activation_authorized") is not True:
        raise OfflinePaperActivationError("paper activation must be authorized")
    if gate.get("activation_allowed") is not False:
        raise OfflinePaperActivationError("source activation_allowed must be false before execution")
    if gate.get("activation_executed") is not False:
        raise OfflinePaperActivationError("authorization was already activated")
    if gate.get("token_consumed") is not False:
        raise OfflinePaperActivationError("activation token was already consumed")
    if gate.get("live_activation_allowed") is not False:
        raise OfflinePaperActivationError("live activation must remain prohibited")
    if gate.get("next_version") != VERSION:
        raise OfflinePaperActivationError("activation gate next_version must be 75.2G")

    token = source.get("activation_token")
    if not isinstance(token, dict):
        raise OfflinePaperActivationError("activation token is required")
    if token.get("single_use") is not True or token.get("consumed") is not False:
        raise OfflinePaperActivationError("activation token must be unused and single-use")
    token_hash = token.get("token_sha256")
    if not isinstance(token_hash, str) or len(token_hash) != 64:
        raise OfflinePaperActivationError("activation token hash is invalid")
    ttl = token.get("ttl_seconds")
    if not isinstance(ttl, int) or ttl <= 0:
        raise OfflinePaperActivationError("activation token ttl is invalid")
    issued_at = parse_iso8601(token.get("issued_at"), "activation_token.issued_at")
    if executed_at < issued_at:
        raise OfflinePaperActivationError("activation cannot execute before token issuance")
    if (executed_at - issued_at).total_seconds() > ttl:
        raise OfflinePaperActivationError("activation token has expired")

    expected_token_payload = {
        "authorization_id": source.get("authorization_id"),
        "decision_id": source.get("decision_id"),
        "session_id": source.get("session_id"),
        "scope": source.get("authorization_scope"),
        "single_use": True,
        "issued_at": token.get("issued_at"),
        "ttl_seconds": ttl,
    }
    if token_hash != sha256_of(expected_token_payload):
        raise OfflinePaperActivationError("activation token integrity failed")

    policy = source.get("runtime_policy")
    if not isinstance(policy, dict) or policy.get("mode") != "OFFLINE_PAPER":
        raise OfflinePaperActivationError("runtime policy must be OFFLINE_PAPER")
    for key in ("network_enabled", "live_orders_enabled", "broker_credentials_required",
                "external_side_effects_allowed"):
        if policy.get(key) is not False:
            raise OfflinePaperActivationError(f"runtime_policy {key} must be false")

    safety = source.get("safety_lock")
    if not isinstance(safety, dict) or safety.get("lock_state") != "ENFORCED":
        raise OfflinePaperActivationError("safety lock must be ENFORCED")
    for key in ("network_enabled", "live_orders_enabled", "broker_credentials_required",
                "external_side_effects_allowed", "automatic_activation_allowed"):
        if safety.get(key) is not False:
            raise OfflinePaperActivationError(f"safety_lock {key} must be false")


def validate_config(config: Dict[str, Any]) -> None:
    for key in (
        "require_valid_single_use_token",
        "require_unexpired_token",
        "consume_token_on_success",
        "initialize_offline_runtime",
        "require_empty_order_queue",
    ):
        if config.get(key) is not True:
            raise OfflinePaperActivationError(f"{key} must be true")
    for key in (
        "network_enabled",
        "live_orders_enabled",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_trading_approval_allowed",
    ):
        if config.get(key) is not False:
            raise OfflinePaperActivationError(f"{key} must be false")


def activation_id(authorization_id: str, session_id: str, executed_at: str) -> str:
    raw = f"{authorization_id}|{session_id}|{executed_at}|{VERSION}"
    return "OPA-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def execute_activation(
    source: Dict[str, Any],
    config: Dict[str, Any],
    executed_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    if executed_at is None:
        executed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    executed_dt = parse_iso8601(executed_at, "executed_at")
    validate_source(source, executed_dt)

    aid = activation_id(source["authorization_id"], source["session_id"], executed_at)
    consumed_token = {
        "token_sha256": source["activation_token"]["token_sha256"],
        "single_use": True,
        "consumed": True,
        "consumed_at": executed_at,
        "authorization_id": source["authorization_id"],
        "activation_id": aid,
    }
    runtime_state = {
        "mode": "OFFLINE_PAPER",
        "state": "ACTIVE",
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "initialized_at": executed_at,
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_connected": False,
        "external_side_effects_allowed": False,
        "order_queue": [],
        "positions_mutated": False,
        "orders_submitted": 0,
    }
    checks = [
        {"check_index": 1, "check": "AUTHORIZATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "AUTHORIZATION_SCOPE", "state": "PASS"},
        {"check_index": 3, "check": "TOKEN_INTEGRITY", "state": "PASS"},
        {"check_index": 4, "check": "TOKEN_EXPIRY", "state": "PASS"},
        {"check_index": 5, "check": "TOKEN_SINGLE_USE_CONSUMPTION", "state": "CONSUMED"},
        {"check_index": 6, "check": "OFFLINE_RUNTIME_INITIALIZATION", "state": "ACTIVE"},
        {"check_index": 7, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "ACTIVATION_AUTHORIZATION_VERIFIED", "state": "PASS", "activation_id": aid},
        {"ledger_index": 2, "event": "ACTIVATION_TOKEN_VALIDATED", "state": "PASS", "activation_id": aid},
        {"ledger_index": 3, "event": "ACTIVATION_TOKEN_CONSUMED", "state": "CONSUMED", "activation_id": aid},
        {"ledger_index": 4, "event": "OFFLINE_PAPER_RUNTIME_INITIALIZED", "state": "ACTIVE", "activation_id": aid},
        {"ledger_index": 5, "event": "LIVE_AND_NETWORK_LOCK_RECONFIRMED", "state": "ENFORCED", "activation_id": aid},
        {"ledger_index": 6, "event": "OFFLINE_PAPER_SESSION_ACTIVATED", "state": "OFFLINE_PAPER_SESSION_ACTIVE", "activation_id": aid},
    ]
    result = {
        "status": "PASS",
        "decision": "offline_paper_activation_executed",
        "activation_id": aid,
        "authorization_id": source["authorization_id"],
        "decision_id": source["decision_id"],
        "review_id": source["review_id"],
        "preflight_id": source["preflight_id"],
        "bundle_id": source["bundle_id"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "activation_state": "OFFLINE_PAPER_SESSION_ACTIVE",
        "authorization_state": "CONSUMED",
        "consumed_activation_token": consumed_token,
        "runtime_state": runtime_state,
        "activation_checks": checks,
        "activation_ledger": ledger,
        "activation_checks_sha256": sha256_of(checks),
        "activation_ledger_sha256": sha256_of(ledger),
        "runtime_state_sha256": sha256_of(runtime_state),
        "source_paper_activation_authorization_sha256": source["paper_activation_authorization_sha256"],
        "activation_gate": {
            "paper_activation_authorized": True,
            "activation_allowed": True,
            "activation_executed": True,
            "token_consumed": True,
            "live_activation_allowed": False,
            "next_version": "75.2H",
        },
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "broker_connected": False,
            "external_side_effects_allowed": False,
            "live_activation_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "orders_submitted": 0,
        "executed_at": executed_at,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_activation_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "offline_paper_activation_record_v75_2g.json": result,
        "offline_paper_runtime_state_v75_2g.json": {
            "activation_id": result["activation_id"],
            "runtime_state": result["runtime_state"],
            "runtime_state_sha256": result["runtime_state_sha256"],
        },
        "offline_paper_activation_checks_v75_2g.json": {
            "activation_id": result["activation_id"],
            "activation_checks": result["activation_checks"],
            "activation_checks_sha256": result["activation_checks_sha256"],
        },
        "offline_paper_activation_ledger_v75_2g.json": {
            "activation_id": result["activation_id"],
            "activation_ledger": result["activation_ledger"],
            "activation_ledger_sha256": result["activation_ledger_sha256"],
        },
        "consumed_activation_token_v75_2g.json": result["consumed_activation_token"],
    }
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (output_dir / "offline_paper_activation_record_v75_2g.sha256").write_text(
        result["offline_paper_activation_sha256"] + "\n", encoding="utf-8"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2G Offline Paper Activation Executor")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--executed-at")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = execute_activation(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.executed_at,
        )
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "activation_id": result["activation_id"],
            "authorization_id": result["authorization_id"],
            "session_id": result["session_id"],
            "activation_state": result["activation_state"],
            "authorization_state": result["authorization_state"],
            "activation_allowed": result["activation_gate"]["activation_allowed"],
            "activation_executed": result["activation_gate"]["activation_executed"],
            "token_consumed": result["activation_gate"]["token_consumed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "orders_submitted": result["orders_submitted"],
            "offline_paper_activation_sha256": result["offline_paper_activation_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (OfflinePaperActivationError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_activation_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
