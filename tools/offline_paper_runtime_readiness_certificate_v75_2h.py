from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2H"
SCHEMA_VERSION = "v75.2h.offline_paper_runtime_readiness_certificate.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2g.offline_paper_activation.1"


class RuntimeReadinessError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeReadinessError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeReadinessError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeReadinessError("top-level JSON must be an object")
    return data


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise RuntimeReadinessError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise RuntimeReadinessError("unsupported source schema_version")
    if source.get("activation_state") != "OFFLINE_PAPER_SESSION_ACTIVE":
        raise RuntimeReadinessError("offline paper session must be active")
    if source.get("authorization_state") != "CONSUMED":
        raise RuntimeReadinessError("authorization must be consumed")
    if source.get("approved_for_live") is not False:
        raise RuntimeReadinessError("approved_for_live must remain false")
    if source.get("network_used") is not False:
        raise RuntimeReadinessError("network_used must remain false")
    if source.get("orders_submitted") != 0:
        raise RuntimeReadinessError("orders_submitted must be zero")

    observed_hash = source.get("offline_paper_activation_sha256")
    if not isinstance(observed_hash, str) or len(observed_hash) != 64:
        raise RuntimeReadinessError("activation record hash is invalid")
    copied = copy.deepcopy(source)
    copied.pop("offline_paper_activation_sha256", None)
    if observed_hash != sha256_of(copied):
        raise RuntimeReadinessError("activation record integrity verification failed")

    checks = source.get("activation_checks")
    if not isinstance(checks, list) or not checks:
        raise RuntimeReadinessError("activation checks are required")
    if source.get("activation_checks_sha256") != sha256_of(checks):
        raise RuntimeReadinessError("activation checks integrity failed")
    if [x.get("check_index") for x in checks] != list(range(1, len(checks) + 1)):
        raise RuntimeReadinessError("activation check indexes must be sequential")

    ledger = source.get("activation_ledger")
    if not isinstance(ledger, list) or not ledger:
        raise RuntimeReadinessError("activation ledger is required")
    if source.get("activation_ledger_sha256") != sha256_of(ledger):
        raise RuntimeReadinessError("activation ledger integrity failed")
    if [x.get("ledger_index") for x in ledger] != list(range(1, len(ledger) + 1)):
        raise RuntimeReadinessError("activation ledger indexes must be sequential")

    gate = source.get("activation_gate")
    if not isinstance(gate, dict):
        raise RuntimeReadinessError("activation gate is required")
    expected_gate = {
        "paper_activation_authorized": True,
        "activation_allowed": True,
        "activation_executed": True,
        "token_consumed": True,
        "live_activation_allowed": False,
        "next_version": VERSION,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise RuntimeReadinessError(f"activation_gate {key} is invalid")

    token = source.get("consumed_activation_token")
    if not isinstance(token, dict):
        raise RuntimeReadinessError("consumed activation token is required")
    if token.get("single_use") is not True or token.get("consumed") is not True:
        raise RuntimeReadinessError("activation token must be consumed and single-use")
    if token.get("activation_id") != source.get("activation_id"):
        raise RuntimeReadinessError("activation token activation_id mismatch")
    if token.get("authorization_id") != source.get("authorization_id"):
        raise RuntimeReadinessError("activation token authorization_id mismatch")
    token_hash = token.get("token_sha256")
    if not isinstance(token_hash, str) or len(token_hash) != 64:
        raise RuntimeReadinessError("consumed activation token hash is invalid")

    runtime = source.get("runtime_state")
    if not isinstance(runtime, dict):
        raise RuntimeReadinessError("runtime_state is required")
    if source.get("runtime_state_sha256") != sha256_of(runtime):
        raise RuntimeReadinessError("runtime_state integrity failed")
    if runtime.get("mode") != "OFFLINE_PAPER" or runtime.get("state") != "ACTIVE":
        raise RuntimeReadinessError("runtime must be active in OFFLINE_PAPER mode")
    if runtime.get("session_id") != source.get("session_id"):
        raise RuntimeReadinessError("runtime session_id mismatch")
    if runtime.get("champion_candidate_id") != source.get("champion_candidate_id"):
        raise RuntimeReadinessError("runtime champion candidate mismatch")
    if runtime.get("order_queue") != []:
        raise RuntimeReadinessError("runtime order queue must be empty")
    if runtime.get("orders_submitted") != 0:
        raise RuntimeReadinessError("runtime orders_submitted must be zero")
    if runtime.get("positions_mutated") is not False:
        raise RuntimeReadinessError("positions must not be mutated before readiness")
    for key in (
        "network_enabled",
        "live_orders_enabled",
        "broker_connected",
        "external_side_effects_allowed",
    ):
        if runtime.get(key) is not False:
            raise RuntimeReadinessError(f"runtime_state {key} must be false")

    safety = source.get("safety_lock")
    if not isinstance(safety, dict) or safety.get("lock_state") != "ENFORCED":
        raise RuntimeReadinessError("safety lock must be ENFORCED")
    for key in (
        "network_enabled",
        "live_orders_enabled",
        "broker_credentials_required",
        "broker_connected",
        "external_side_effects_allowed",
        "live_activation_allowed",
    ):
        if safety.get(key) is not False:
            raise RuntimeReadinessError(f"safety_lock {key} must be false")


def validate_config(config: Dict[str, Any]) -> None:
    for key in (
        "require_active_offline_runtime",
        "require_consumed_single_use_token",
        "require_empty_order_queue",
        "require_zero_submitted_orders",
        "require_unmutated_positions",
        "issue_readiness_certificate",
    ):
        if config.get(key) is not True:
            raise RuntimeReadinessError(f"{key} must be true")
    for key in (
        "network_enabled",
        "live_orders_enabled",
        "broker_credentials_required",
        "broker_connected",
        "external_side_effects_allowed",
        "live_trading_approval_allowed",
    ):
        if config.get(key) is not False:
            raise RuntimeReadinessError(f"{key} must be false")


def certificate_id(activation_id: str, session_id: str, certified_at: str) -> str:
    raw = f"{activation_id}|{session_id}|{certified_at}|{VERSION}"
    return "PRC-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def build_certificate(
    source: Dict[str, Any],
    config: Dict[str, Any],
    certified_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)
    if certified_at is None:
        certified_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    cid = certificate_id(source["activation_id"], source["session_id"], certified_at)
    readiness_checks = [
        {"check_index": 1, "check": "ACTIVATION_RECORD_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "OFFLINE_RUNTIME_ACTIVE", "state": "PASS"},
        {"check_index": 3, "check": "SINGLE_USE_TOKEN_CONSUMED", "state": "PASS"},
        {"check_index": 4, "check": "ORDER_QUEUE_EMPTY", "state": "PASS"},
        {"check_index": 5, "check": "ORDERS_SUBMITTED_ZERO", "state": "PASS"},
        {"check_index": 6, "check": "POSITIONS_UNMUTATED", "state": "PASS"},
        {"check_index": 7, "check": "BROKER_DISCONNECTED", "state": "PASS"},
        {"check_index": 8, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 9, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    readiness_ledger = [
        {"ledger_index": 1, "event": "ACTIVATION_RECORD_VERIFIED", "state": "PASS", "certificate_id": cid},
        {"ledger_index": 2, "event": "RUNTIME_STATE_VERIFIED", "state": "PASS", "certificate_id": cid},
        {"ledger_index": 3, "event": "TOKEN_CONSUMPTION_VERIFIED", "state": "PASS", "certificate_id": cid},
        {"ledger_index": 4, "event": "SAFETY_LOCKS_RECONFIRMED", "state": "ENFORCED", "certificate_id": cid},
        {"ledger_index": 5, "event": "READINESS_CERTIFICATE_ISSUED", "state": "READY_FOR_OFFLINE_PAPER_CYCLE", "certificate_id": cid},
    ]
    runtime_snapshot = {
        "session_id": source["session_id"],
        "activation_id": source["activation_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "mode": source["runtime_state"]["mode"],
        "state": source["runtime_state"]["state"],
        "order_queue_size": len(source["runtime_state"]["order_queue"]),
        "orders_submitted": source["runtime_state"]["orders_submitted"],
        "positions_mutated": source["runtime_state"]["positions_mutated"],
        "broker_connected": source["runtime_state"]["broker_connected"],
        "network_enabled": source["runtime_state"]["network_enabled"],
        "live_orders_enabled": source["runtime_state"]["live_orders_enabled"],
    }
    result = {
        "status": "PASS",
        "decision": "offline_paper_runtime_readiness_certified",
        "certificate_id": cid,
        "certificate_state": "READY_FOR_OFFLINE_PAPER_CYCLE",
        "activation_id": source["activation_id"],
        "authorization_id": source["authorization_id"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "runtime_snapshot": runtime_snapshot,
        "readiness_checks": readiness_checks,
        "readiness_ledger": readiness_ledger,
        "runtime_snapshot_sha256": sha256_of(runtime_snapshot),
        "readiness_checks_sha256": sha256_of(readiness_checks),
        "readiness_ledger_sha256": sha256_of(readiness_ledger),
        "source_offline_paper_activation_sha256": source["offline_paper_activation_sha256"],
        "readiness_gate": {
            "offline_paper_runtime_ready": True,
            "offline_paper_cycle_allowed": True,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "operator_cycle_start_required": True,
            "next_version": "75.2I",
        },
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "broker_connected": False,
            "external_side_effects_allowed": False,
            "live_trading_approval_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "orders_submitted": 0,
        "certified_at": certified_at,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_runtime_readiness_certificate_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "offline_paper_runtime_readiness_certificate_v75_2h.json": result,
        "offline_paper_runtime_readiness_checks_v75_2h.json": {
            "certificate_id": result["certificate_id"],
            "readiness_checks": result["readiness_checks"],
            "readiness_checks_sha256": result["readiness_checks_sha256"],
        },
        "offline_paper_runtime_readiness_ledger_v75_2h.json": {
            "certificate_id": result["certificate_id"],
            "readiness_ledger": result["readiness_ledger"],
            "readiness_ledger_sha256": result["readiness_ledger_sha256"],
        },
        "offline_paper_runtime_snapshot_v75_2h.json": {
            "certificate_id": result["certificate_id"],
            "runtime_snapshot": result["runtime_snapshot"],
            "runtime_snapshot_sha256": result["runtime_snapshot_sha256"],
        },
    }
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (output_dir / "offline_paper_runtime_readiness_certificate_v75_2h.sha256").write_text(
        result["offline_paper_runtime_readiness_certificate_sha256"] + "\n",
        encoding="utf-8",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2H Offline Paper Runtime Readiness Certificate")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_certificate(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
        )
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "certificate_id": result["certificate_id"],
            "certificate_state": result["certificate_state"],
            "activation_id": result["activation_id"],
            "session_id": result["session_id"],
            "offline_paper_runtime_ready": result["readiness_gate"]["offline_paper_runtime_ready"],
            "offline_paper_cycle_allowed": result["readiness_gate"]["offline_paper_cycle_allowed"],
            "paper_orders_allowed": result["readiness_gate"]["paper_orders_allowed"],
            "live_orders_allowed": result["readiness_gate"]["live_orders_allowed"],
            "network_allowed": result["readiness_gate"]["network_allowed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "orders_submitted": result["orders_submitted"],
            "offline_paper_runtime_readiness_certificate_sha256":
                result["offline_paper_runtime_readiness_certificate_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (RuntimeReadinessError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_runtime_readiness_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
