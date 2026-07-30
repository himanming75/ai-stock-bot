from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2K"
SCHEMA_VERSION = "v75.2k.offline_paper_cycle_runtime_baseline_certificate.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2j.offline_paper_cycle_start_execution.1"


class BaselineCertificateError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BaselineCertificateError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineCertificateError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise BaselineCertificateError("top-level JSON must be an object")
    return value


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise BaselineCertificateError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise BaselineCertificateError("unsupported source schema_version")
    if source.get("execution_state") != "OFFLINE_PAPER_CYCLE_ACTIVE":
        raise BaselineCertificateError("cycle execution must be active")
    if source.get("authorization_state") != "CONSUMED":
        raise BaselineCertificateError("authorization must be consumed")
    if source.get("cycle_start_authorized") is not True:
        raise BaselineCertificateError("cycle start authorization is missing")
    if source.get("cycle_started") is not True:
        raise BaselineCertificateError("cycle must already be started")
    if source.get("approved_for_live") is not False:
        raise BaselineCertificateError("approved_for_live must remain false")
    if source.get("network_used") is not False:
        raise BaselineCertificateError("network_used must remain false")
    if source.get("orders_submitted") != 0:
        raise BaselineCertificateError("orders_submitted must be zero")

    observed = source.get("offline_paper_cycle_start_execution_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise BaselineCertificateError("source execution SHA256 is invalid")
    copied = copy.deepcopy(source)
    copied.pop("offline_paper_cycle_start_execution_sha256", None)
    if sha256_of(copied) != observed:
        raise BaselineCertificateError("source execution integrity verification failed")

    checks = source.get("execution_checks")
    if not isinstance(checks, list) or not checks:
        raise BaselineCertificateError("execution checks are required")
    if source.get("execution_checks_sha256") != sha256_of(checks):
        raise BaselineCertificateError("execution checks integrity failed")
    if [x.get("check_index") for x in checks] != list(range(1, len(checks) + 1)):
        raise BaselineCertificateError("execution check indexes must be sequential")

    ledger = source.get("execution_ledger")
    if not isinstance(ledger, list) or not ledger:
        raise BaselineCertificateError("execution ledger is required")
    if source.get("execution_ledger_sha256") != sha256_of(ledger):
        raise BaselineCertificateError("execution ledger integrity failed")
    if [x.get("ledger_index") for x in ledger] != list(range(1, len(ledger) + 1)):
        raise BaselineCertificateError("execution ledger indexes must be sequential")

    token = source.get("consumed_cycle_start_token")
    if not isinstance(token, dict):
        raise BaselineCertificateError("consumed cycle start token is required")
    if source.get("consumed_cycle_start_token_sha256") != sha256_of(token):
        raise BaselineCertificateError("consumed token integrity failed")
    if token.get("single_use") is not True or token.get("consumed") is not True:
        raise BaselineCertificateError("cycle start token must be consumed")
    if token.get("consumed_by_execution_id") != source.get("execution_id"):
        raise BaselineCertificateError("token execution_id mismatch")
    if token.get("session_id") != source.get("session_id"):
        raise BaselineCertificateError("token session_id mismatch")

    state = source.get("cycle_state")
    if not isinstance(state, dict):
        raise BaselineCertificateError("cycle_state is required")
    if source.get("cycle_state_sha256") != sha256_of(state):
        raise BaselineCertificateError("cycle_state integrity failed")
    expected_state = {
        "cycle_id": source.get("cycle_id"),
        "cycle_sequence": source.get("cycle_sequence"),
        "session_id": source.get("session_id"),
        "champion_candidate_id": source.get("champion_candidate_id"),
        "mode": "OFFLINE_PAPER",
        "state": "ACTIVE",
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
    for key, expected in expected_state.items():
        if state.get(key) != expected:
            raise BaselineCertificateError(f"cycle_state {key} is invalid")

    gate = source.get("execution_gate")
    expected_gate = {
        "cycle_active": True,
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise BaselineCertificateError("execution_gate is required")
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise BaselineCertificateError(f"execution_gate {key} is invalid")

    for key in (
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
    ):
        if source.get(key) is not False:
            raise BaselineCertificateError(f"{key} must be false")

    lock = source.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise BaselineCertificateError("safety lock must be ENFORCED")
    for key in (
        "broker_connected",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_orders_enabled",
        "live_trading_approval_allowed",
        "network_enabled",
    ):
        if lock.get(key) is not False:
            raise BaselineCertificateError(f"safety_lock {key} must be false")


def validate_config(config: Dict[str, Any]) -> None:
    for key in (
        "require_active_cycle",
        "require_consumed_start_token",
        "require_empty_order_queue",
        "require_zero_orders",
        "require_unmutated_positions",
        "require_signal_generation_not_started",
        "require_order_generation_not_started",
        "require_fill_simulation_not_started",
    ):
        if config.get(key) is not True:
            raise BaselineCertificateError(f"{key} must be true")
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
            raise BaselineCertificateError(f"{key} must be false")


def certificate_id(execution_id: str, certified_at: str) -> str:
    material = f"{execution_id}|{certified_at}|{VERSION}"
    return "PBC-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def build_certificate(
    source: Dict[str, Any],
    config: Dict[str, Any],
    certified_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)
    if certified_at is None:
        when = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        try:
            when = datetime.fromisoformat(certified_at)
        except ValueError as exc:
            raise BaselineCertificateError("certified_at must be ISO-8601") from exc
        if when.tzinfo is None:
            raise BaselineCertificateError("certified_at must include timezone")
    certified_at_value = when.isoformat()
    cid = certificate_id(source["execution_id"], certified_at_value)

    snapshot = copy.deepcopy(source["cycle_state"])
    snapshot["baseline_observed_at"] = certified_at_value

    checks = [
        {"check_index": 1, "check": "CYCLE_START_EXECUTION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "CYCLE_ACTIVE", "state": "PASS"},
        {"check_index": 3, "check": "START_TOKEN_CONSUMED", "state": "PASS"},
        {"check_index": 4, "check": "SIGNAL_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 5, "check": "ORDER_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 6, "check": "FILL_SIMULATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 7, "check": "ORDER_QUEUE_EMPTY", "state": "PASS"},
        {"check_index": 8, "check": "ORDERS_SUBMITTED_ZERO", "state": "PASS"},
        {"check_index": 9, "check": "POSITIONS_UNMUTATED", "state": "PASS"},
        {"check_index": 10, "check": "BROKER_DISCONNECTED", "state": "PASS"},
        {"check_index": 11, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "CYCLE_START_EXECUTION_VERIFIED", "state": "PASS", "certificate_id": cid},
        {"ledger_index": 2, "event": "ACTIVE_CYCLE_STATE_VERIFIED", "state": "PASS", "certificate_id": cid},
        {"ledger_index": 3, "event": "PRE_SIGNAL_BASELINE_VERIFIED", "state": "PASS", "certificate_id": cid},
        {"ledger_index": 4, "event": "SAFETY_LOCKS_RECONFIRMED", "state": "ENFORCED", "certificate_id": cid},
        {"ledger_index": 5, "event": "RUNTIME_BASELINE_CERTIFICATE_ISSUED", "state": "READY_FOR_SIGNAL_INPUT_PREPARATION", "certificate_id": cid},
    ]

    result = {
        "status": "PASS",
        "decision": "offline_paper_cycle_runtime_baseline_certified",
        "certificate_id": cid,
        "certificate_state": "READY_FOR_SIGNAL_INPUT_PREPARATION",
        "execution_id": source["execution_id"],
        "authorization_id": source["authorization_id"],
        "activation_id": source["activation_id"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "cycle_active": True,
        "baseline_snapshot": snapshot,
        "baseline_checks": checks,
        "baseline_ledger": ledger,
        "baseline_snapshot_sha256": sha256_of(snapshot),
        "baseline_checks_sha256": sha256_of(checks),
        "baseline_ledger_sha256": sha256_of(ledger),
        "source_cycle_start_execution_sha256":
            source["offline_paper_cycle_start_execution_sha256"],
        "baseline_gate": {
            "runtime_baseline_certified": True,
            "signal_input_preparation_allowed": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2L",
        },
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(source["safety_lock"]),
        "certified_at": certified_at_value,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_cycle_runtime_baseline_certificate_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_cycle_runtime_baseline_certificate_v75_2k.json": result,
        "offline_paper_cycle_runtime_baseline_checks_v75_2k.json": {
            "certificate_id": result["certificate_id"],
            "baseline_checks": result["baseline_checks"],
            "baseline_checks_sha256": result["baseline_checks_sha256"],
        },
        "offline_paper_cycle_runtime_baseline_ledger_v75_2k.json": {
            "certificate_id": result["certificate_id"],
            "baseline_ledger": result["baseline_ledger"],
            "baseline_ledger_sha256": result["baseline_ledger_sha256"],
        },
        "offline_paper_cycle_runtime_baseline_snapshot_v75_2k.json":
            result["baseline_snapshot"],
    }
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (output_dir / "offline_paper_cycle_runtime_baseline_certificate_v75_2k.sha256").write_text(
        result["offline_paper_cycle_runtime_baseline_certificate_sha256"] + "\n",
        encoding="utf-8",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V75.2K Offline Paper Cycle Runtime Baseline Certificate"
    )
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--certified-at")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_certificate(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.certified_at,
        )
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "certificate_id": result["certificate_id"],
            "certificate_state": result["certificate_state"],
            "execution_id": result["execution_id"],
            "session_id": result["session_id"],
            "cycle_id": result["cycle_id"],
            "cycle_sequence": result["cycle_sequence"],
            "cycle_active": result["cycle_active"],
            "runtime_baseline_certified":
                result["baseline_gate"]["runtime_baseline_certified"],
            "signal_input_preparation_allowed":
                result["baseline_gate"]["signal_input_preparation_allowed"],
            "signal_generation_allowed":
                result["baseline_gate"]["signal_generation_allowed"],
            "order_generation_allowed":
                result["baseline_gate"]["order_generation_allowed"],
            "fill_simulation_allowed":
                result["baseline_gate"]["fill_simulation_allowed"],
            "paper_orders_allowed": result["paper_orders_allowed"],
            "live_orders_allowed": result["live_orders_allowed"],
            "network_allowed": result["network_allowed"],
            "orders_submitted": result["orders_submitted"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "offline_paper_cycle_runtime_baseline_certificate_sha256":
                result["offline_paper_cycle_runtime_baseline_certificate_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (BaselineCertificateError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_cycle_runtime_baseline_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
