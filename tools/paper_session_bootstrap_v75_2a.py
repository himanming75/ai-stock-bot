from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "75.2A"
SCHEMA_VERSION = "v75.2a.paper_session_bootstrap.1"
SUPPORTED_SOURCE_SCHEMA = "v75.1c.rollback_manifest.1"


class PaperSessionBootstrapError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PaperSessionBootstrapError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PaperSessionBootstrapError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PaperSessionBootstrapError("top-level JSON must be an object")
    return data


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise PaperSessionBootstrapError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PaperSessionBootstrapError("unsupported source schema_version")
    if source.get("rollback_state") != "READY_FOR_PAPER_SESSION_BOOTSTRAP":
        raise PaperSessionBootstrapError(
            "rollback_state must be READY_FOR_PAPER_SESSION_BOOTSTRAP"
        )
    if source.get("promotion_scope") != "PROVISIONAL_PAPER_ONLY":
        raise PaperSessionBootstrapError(
            "promotion_scope must be PROVISIONAL_PAPER_ONLY"
        )
    if source.get("approved_for_live") is not False:
        raise PaperSessionBootstrapError("source approved_for_live must be false")
    if source.get("network_used") is not False:
        raise PaperSessionBootstrapError("source network_used must be false")

    champion_id = source.get("champion_candidate_id")
    if not champion_id:
        raise PaperSessionBootstrapError("champion_candidate_id is required")

    paper_ref = source.get("paper_session_reference")
    if not isinstance(paper_ref, dict):
        raise PaperSessionBootstrapError("paper_session_reference is required")
    if paper_ref.get("bootstrap_version") != VERSION:
        raise PaperSessionBootstrapError(
            "paper_session_reference.bootstrap_version must be 75.2A"
        )
    if paper_ref.get("bootstrap_allowed") is not True:
        raise PaperSessionBootstrapError("bootstrap_allowed must be true")
    if paper_ref.get("activation_allowed") is not False:
        raise PaperSessionBootstrapError("activation_allowed must be false")

    observed_hash = source.get("rollback_manifest_sha256")
    if not isinstance(observed_hash, str) or len(observed_hash) != 64:
        raise PaperSessionBootstrapError("rollback_manifest_sha256 is invalid")

    copied = dict(source)
    copied.pop("rollback_manifest_sha256", None)
    expected_hash = sha256_of(copied)
    if observed_hash != expected_hash:
        raise PaperSessionBootstrapError(
            "rollback manifest integrity verification failed"
        )


def validate_config(config: Dict[str, Any]) -> None:
    starting_cash = config.get("starting_cash")
    if not isinstance(starting_cash, (int, float)) or starting_cash <= 0:
        raise PaperSessionBootstrapError("starting_cash must be positive")

    currency = config.get("currency")
    if not isinstance(currency, str) or not currency:
        raise PaperSessionBootstrapError("currency is required")

    max_positions = config.get("max_positions")
    if not isinstance(max_positions, int) or max_positions < 1:
        raise PaperSessionBootstrapError("max_positions must be at least 1")

    session_mode = config.get("session_mode")
    if session_mode != "OFFLINE_PAPER":
        raise PaperSessionBootstrapError(
            "session_mode must be OFFLINE_PAPER"
        )

    if config.get("network_enabled") is not False:
        raise PaperSessionBootstrapError("network_enabled must be false")
    if config.get("live_orders_enabled") is not False:
        raise PaperSessionBootstrapError("live_orders_enabled must be false")


def deterministic_session_id(
    champion_id: str,
    source_hash: str,
    created_at: str,
) -> str:
    payload = f"{champion_id}|{source_hash}|{created_at}|{VERSION}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()
    return f"PAPER-{digest}"


def build_bootstrap(
    source: Dict[str, Any],
    config: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    champion_id = source["champion_candidate_id"]
    runner_up_id = source.get("runner_up_candidate_id")
    session_id = deterministic_session_id(
        champion_id,
        source["rollback_manifest_sha256"],
        created_at,
    )

    account_state = {
        "currency": config["currency"],
        "starting_cash": float(config["starting_cash"]),
        "cash": float(config["starting_cash"]),
        "equity": float(config["starting_cash"]),
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "positions": [],
        "open_orders": [],
        "closed_orders": [],
        "max_positions": config["max_positions"],
        "account_state": "INITIALIZED",
    }
    account_state["account_state_sha256"] = sha256_of(account_state)

    health_check = {
        "session_id": session_id,
        "bootstrap_integrity": "PASS",
        "account_initialized": True,
        "champion_attached": True,
        "rollback_manifest_attached": True,
        "network_disabled": True,
        "live_orders_disabled": True,
        "paper_activation_state": "NOT_ACTIVATED",
        "health_state": "READY",
    }
    health_check["health_check_sha256"] = sha256_of(health_check)

    ledger = [
        {
            "ledger_index": 1,
            "event": "PAPER_SESSION_ID_CREATED",
            "session_id": session_id,
            "state": "CREATED",
        },
        {
            "ledger_index": 2,
            "event": "PAPER_ACCOUNT_INITIALIZED",
            "session_id": session_id,
            "state": "READY",
        },
        {
            "ledger_index": 3,
            "event": "CHAMPION_ATTACHED",
            "session_id": session_id,
            "candidate_id": champion_id,
            "state": "ATTACHED",
        },
        {
            "ledger_index": 4,
            "event": "ROLLBACK_MANIFEST_ATTACHED",
            "session_id": session_id,
            "state": "ATTACHED",
        },
        {
            "ledger_index": 5,
            "event": "PAPER_SESSION_BOOTSTRAP_CREATED",
            "session_id": session_id,
            "state": "READY",
        },
    ]

    bootstrap = {
        "status": "PASS",
        "decision": "paper_session_bootstrap_created",
        "bootstrap_state": "READY_FOR_PAPER_DEPLOYMENT_BUNDLE",
        "session_id": session_id,
        "session_mode": "OFFLINE_PAPER",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": champion_id,
        "runner_up_candidate_id": runner_up_id,
        "strategy_binding": {
            "candidate_id": champion_id,
            "binding_state": "ATTACHED_NOT_ACTIVATED",
            "runner_up_failover_candidate_id": runner_up_id,
        },
        "account_state": account_state,
        "health_check": health_check,
        "session_ledger": ledger,
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "lock_state": "ENFORCED",
        },
        "activation_gate": {
            "activation_allowed": False,
            "requires_deployment_bundle": True,
            "requires_operator_review": True,
            "next_version": "75.2B",
        },
        "created_at": created_at,
        "approved_for_live": False,
        "network_used": False,
        "source_rollback_manifest_sha256": source[
            "rollback_manifest_sha256"
        ],
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    bootstrap["session_ledger_sha256"] = sha256_of(ledger)
    bootstrap["paper_session_bootstrap_sha256"] = sha256_of(bootstrap)
    return bootstrap


def write_outputs(bootstrap: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "paper_session_bootstrap_v75_2a.json": bootstrap,
        "paper_account_state_v75_2a.json": bootstrap["account_state"],
        "paper_session_health_v75_2a.json": bootstrap["health_check"],
        "paper_session_ledger_v75_2a.json": {
            "session_ledger": bootstrap["session_ledger"],
            "session_ledger_sha256": bootstrap["session_ledger_sha256"],
        },
    }

    for filename, data in outputs.items():
        (output_dir / filename).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (output_dir / "paper_session_bootstrap_v75_2a.sha256").write_text(
        bootstrap["paper_session_bootstrap_sha256"] + "\n",
        encoding="utf-8",
    )


def run(
    input_path: Path,
    config_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    source = read_json(input_path)
    config = read_json(config_path)
    bootstrap = build_bootstrap(source, config)
    write_outputs(bootstrap, output_dir)
    return bootstrap


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.2A Paper Session Bootstrap Builder"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        bootstrap = run(args.input, args.config, args.output_dir)
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "paper_session_bootstrap_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": bootstrap["status"],
        "decision": bootstrap["decision"],
        "bootstrap_state": bootstrap["bootstrap_state"],
        "session_id": bootstrap["session_id"],
        "champion_candidate_id": bootstrap["champion_candidate_id"],
        "runner_up_candidate_id": bootstrap["runner_up_candidate_id"],
        "starting_cash": bootstrap["account_state"]["starting_cash"],
        "currency": bootstrap["account_state"]["currency"],
        "health_state": bootstrap["health_check"]["health_state"],
        "activation_allowed": bootstrap["activation_gate"][
            "activation_allowed"
        ],
        "approved_for_live": bootstrap["approved_for_live"],
        "network_used": bootstrap["network_used"],
        "paper_session_bootstrap_sha256": bootstrap[
            "paper_session_bootstrap_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
