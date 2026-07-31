from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from broker.contracts_v77_1 import (
    BrokerContract,
    BrokerOrderRequest,
    BrokerOrderStatus,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.sandbox_adapter_v77_2 import SandboxBrokerAdapter, SandboxBrokerError

VERSION = "77.2"
SCHEMA = "v77.2.sandbox_broker_adapter.1"
NEXT_PHASE = "V77_3_ORDER_LIFECYCLE_SIMULATOR"


class AdapterVerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AdapterVerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AdapterVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise AdapterVerificationError(f"JSON root must be object: {path}")
    return value


def run_git(root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if process.returncode != 0:
        raise AdapterVerificationError(
            f"git {' '.join(args)} failed: {process.stderr.strip()}"
        )
    return process.stdout.strip()


V77_2_ALLOWED_TRACKED_PATHS = frozenset(
    {
        "V77_2_INSTALL_AND_EXECUTION_CHECK.txt",
        "broker/__init__.py",
        "broker/sandbox_adapter_v77_2.py",
        "tools/sandbox_broker_adapter_v77_2.py",
        "tools/verify_sandbox_broker_adapter_v77_2.py",
        "tools/test_sandbox_broker_adapter_v77_2.py",
        "release/v77_2/config/sandbox_broker_adapter_config_v77_2.json",
        "release/v77_2/docs/V77_2_SANDBOX_BROKER_ADAPTER.md",
    }
)


def _status_path(line: str) -> str:
    value = line[3:].strip()
    if " -> " in value:
        value = value.split(" -> ", 1)[1]
    return value.replace("\\", "/")


def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    tracked_lines = tracked.splitlines() if tracked else []
    unrelated = [
        line for line in tracked_lines
        if _status_path(line) not in V77_2_ALLOWED_TRACKED_PATHS
    ]
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "head_short_sha": run_git(root, ["rev-parse", "--short=7", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked_lines,
        "unrelated_tracked_status_short": unrelated,
    }


def git_is_ancestor(root: Path, ancestor: str, descendant: str = "HEAD") -> bool:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode not in {0, 1}:
        raise AdapterVerificationError(
            f"git merge-base --is-ancestor failed: {process.stderr.strip()}"
        )
    return process.returncode == 0


def validate_config(config: dict[str, Any]) -> None:
    if config.get("adapter_scope") != "SANDBOX_BROKER_ADAPTER":
        raise AdapterVerificationError("adapter_scope invalid")
    if config.get("required_environment") != "offline":
        raise AdapterVerificationError("required_environment must be offline")
    Decimal(config.get("starting_cash", ""))
    for key in (
        "require_duplicate_client_order_id_rejection",
        "require_cancel_support",
        "require_zero_actual_orders",
        "require_event_ledger",
    ):
        if config.get(key) is not True:
            raise AdapterVerificationError(f"{key} must be true")
    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "actual_order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
        "fills_allowed",
    ):
        if config.get(key) is not False:
            raise AdapterVerificationError(f"{key} must be false")


def add_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool) -> None:
    gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL"})


def verify_adapter(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(
        gates,
        "GIT_FRAMEWORK_COMMIT_IS_ANCESTOR",
        git_is_ancestor(root, config["expected_framework_commit_sha"]),
    )
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(
        gates,
        "GIT_NO_UNRELATED_TRACKED_CHANGES",
        git["unrelated_tracked_status_short"] == [],
    )

    v77_1_path = root / "release/v77_1/output/broker_interface_contract_verification_v77_1.json"
    add_gate(gates, "V77_1_VERIFICATION_EXISTS", v77_1_path.is_file())
    source = load_json(v77_1_path)
    add_gate(gates, "V77_1_STATUS_PASS", source.get("status") == "PASS")
    add_gate(
        gates, "V77_1_CONTRACT_ANCHOR_MATCH",
        source.get("broker_contract_sha256")
        == config["expected_v77_1_broker_contract_sha256"],
    )
    add_gate(
        gates, "V77_1_VERIFICATION_ANCHOR_MATCH",
        source.get("verification_sha256")
        == config["expected_v77_1_verification_sha256"],
    )
    add_gate(
        gates, "V77_1_NEXT_PHASE_MATCH",
        source.get("next_phase") == "V77_2_SANDBOX_BROKER_ADAPTER",
    )

    adapter = SandboxBrokerAdapter(starting_cash=Decimal(config["starting_cash"]))
    add_gate(gates, "BROKER_CONTRACT_RUNTIME_MATCH", isinstance(adapter, BrokerContract))

    health = adapter.health()
    add_gate(gates, "ADAPTER_NAME_MATCH", health.adapter_name == config["required_adapter_name"])
    add_gate(gates, "ENVIRONMENT_OFFLINE", health.environment.value == "offline")
    add_gate(gates, "BROKER_DISCONNECTED", health.connected is False)
    add_gate(gates, "BROKER_UNAUTHENTICATED", health.authenticated is False)
    add_gate(gates, "NETWORK_UNUSED", health.network_used is False)
    add_gate(gates, "ACTUAL_ORDER_COUNT_ZERO_INITIAL", adapter.actual_orders_submitted == 0)

    request = BrokerOrderRequest(
        client_order_id="v77-2-verification-order-0001",
        symbol="aapl",
        side=OrderSide.BUY,
        quantity=Decimal("2"),
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("190.00"),
        strategy_id="v77-2-verifier",
    )
    accepted = adapter.submit_order(request)
    add_gate(gates, "SIMULATED_ORDER_ACCEPTED", accepted.status is BrokerOrderStatus.ACCEPTED)
    add_gate(gates, "SYMBOL_NORMALIZED", accepted.request.symbol == "AAPL")
    add_gate(gates, "SIMULATED_ORDER_RETRIEVABLE", adapter.get_order(accepted.broker_order_id) == accepted)
    add_gate(gates, "SIMULATED_ORDER_LISTED", len(adapter.list_orders()) == 1)
    add_gate(gates, "OPEN_ORDER_IN_ACCOUNT_SNAPSHOT", len(adapter.get_account_snapshot().open_orders) == 1)
    add_gate(gates, "NO_FILL_CREATED", accepted.filled_quantity == Decimal("0"))

    duplicate_rejected = False
    try:
        adapter.submit_order(request)
    except SandboxBrokerError:
        duplicate_rejected = True
    add_gate(gates, "DUPLICATE_CLIENT_ORDER_ID_REJECTED", duplicate_rejected)

    canceled = adapter.cancel_order(accepted.broker_order_id)
    add_gate(gates, "SIMULATED_ORDER_CANCELED", canceled.status is BrokerOrderStatus.CANCELED)
    add_gate(gates, "CANCELED_REMOVED_FROM_OPEN_ORDERS", adapter.get_account_snapshot().open_orders == ())
    add_gate(gates, "ACTUAL_ORDER_COUNT_REMAINS_ZERO", adapter.actual_orders_submitted == 0)

    events = adapter.event_ledger()
    event_types = [event.event_type for event in events]
    add_gate(gates, "EVENT_LEDGER_PRESENT", len(events) >= 4)
    add_gate(gates, "ACCEPT_EVENT_RECORDED", "simulated_order_accepted" in event_types)
    add_gate(gates, "DUPLICATE_EVENT_RECORDED", "duplicate_order_rejected" in event_types)
    add_gate(gates, "CANCEL_EVENT_RECORDED", "simulated_order_canceled" in event_types)

    adapter_definition = {
        "adapter_name": adapter.ADAPTER_NAME,
        "capabilities": {
            "market": adapter.capabilities.supports_market_orders,
            "limit": adapter.capabilities.supports_limit_orders,
            "stop": adapter.capabilities.supports_stop_orders,
            "stop_limit": adapter.capabilities.supports_stop_limit_orders,
            "cancel": adapter.capabilities.supports_cancel,
            "replace": adapter.capabilities.supports_replace,
            "fractional": adapter.capabilities.supports_fractional_quantity,
            "time_in_force": [v.value for v in adapter.capabilities.supported_time_in_force],
        },
        "supported_statuses_v77_2": [
            BrokerOrderStatus.ACCEPTED.value,
            BrokerOrderStatus.CANCELED.value,
        ],
        "actual_network_calls": 0,
        "actual_orders_submitted": 0,
        "fills_created": 0,
    }
    adapter_sha = digest(adapter_definition)
    add_gate(gates, "ADAPTER_DIGEST_CREATED", len(adapter_sha) == 64)

    failed = [gate["gate_id"] for gate in gates if gate["status"] == "FAIL"]
    status = "PASS" if not failed else "FAIL"
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "record_type": "SANDBOX_BROKER_ADAPTER_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "decision": (
            "sandbox_broker_adapter_established"
            if status == "PASS" else "sandbox_broker_adapter_rejected"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "no_unrelated_tracked_changes": git["unrelated_tracked_status_short"] == [],
            "allowed_v77_2_tracked_changes": git["tracked_status_short"],
        },
        "source_anchors": {
            "v77_1_broker_contract_sha256": source.get("broker_contract_sha256"),
            "v77_1_verification_sha256": source.get("verification_sha256"),
        },
        "adapter_definition": adapter_definition,
        "sandbox_broker_adapter_sha256": adapter_sha,
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "environment": "offline",
        "network_allowed": False,
        "broker_connected": False,
        "simulated_orders_accepted": 1,
        "simulated_orders_canceled": 1,
        "actual_orders_submitted": 0,
        "fills_created": 0,
        "order_submission_allowed": False,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS" else "REPAIR_V77_2_SANDBOX_BROKER_ADAPTER",
    }
    result["verification_sha256"] = digest(
        {k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc"}}
    )
    return result


def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    vr = result["verification_result"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "sandbox_broker_adapter_sha256": result["sandbox_broker_adapter_sha256"],
        "verification_sha256": result["verification_sha256"],
        **result["source_anchors"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "environment": result["environment"],
        "network_allowed": result["network_allowed"],
        "broker_connected": result["broker_connected"],
        "simulated_orders_accepted": result["simulated_orders_accepted"],
        "simulated_orders_canceled": result["simulated_orders_canceled"],
        "actual_orders_submitted": result["actual_orders_submitted"],
        "fills_created": result["fills_created"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sandbox_broker_adapter_verification_v77_2.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "sandbox_broker_adapter_summary_v77_2.json").write_text(
        json.dumps(summary_from(result), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = verify_adapter(Path(args.repository_root), load_json(Path(args.config)))
    write_outputs(result, Path(args.output_dir))
    print(json.dumps(summary_from(result), indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
