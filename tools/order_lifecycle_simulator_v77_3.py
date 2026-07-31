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
    BrokerOrderRequest,
    BrokerOrderStatus,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from broker.sandbox_adapter_v77_2 import SandboxBrokerError

VERSION = "77.3"
SCHEMA = "v77.3.order_lifecycle_simulator.1"
NEXT_PHASE = "V77_4_EXECUTION_EVENT_RECONCILIATION"


class VerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root must be object: {path}")
    return value


def run_git(root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if process.returncode != 0:
        raise VerificationError(f"git {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def git_is_ancestor(root: Path, ancestor: str, descendant: str = "HEAD") -> bool:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )
    if process.returncode not in {0, 1}:
        raise VerificationError(process.stderr.strip())
    return process.returncode == 0


def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
    }


def add_gate(gates: list[dict[str, str]], gate_id: str, passed: bool) -> None:
    gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL"})


def verify(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    git = git_state(root)
    gates: list[dict[str, str]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(
        gates,
        "GIT_FRAMEWORK_COMMIT_IS_ANCESTOR",
        git_is_ancestor(root, config["expected_framework_commit_sha"]),
    )

    source_path = root / "release/v77_2/output/sandbox_broker_adapter_verification_v77_2.json"
    add_gate(gates, "V77_2_VERIFICATION_EXISTS", source_path.is_file())
    source = load_json(source_path)
    add_gate(gates, "V77_2_STATUS_PASS", source.get("status") == "PASS")
    add_gate(
        gates, "V77_2_ADAPTER_ANCHOR_MATCH",
        source.get("sandbox_broker_adapter_sha256")
        == config["expected_v77_2_adapter_sha256"],
    )
    add_gate(
        gates, "V77_2_VERIFICATION_ANCHOR_MATCH",
        source.get("verification_sha256")
        == config["expected_v77_2_verification_sha256"],
    )
    add_gate(
        gates, "V77_2_NEXT_PHASE_MATCH",
        source.get("next_phase") == "V77_3_ORDER_LIFECYCLE_SIMULATOR",
    )

    sim = OrderLifecycleSimulator(starting_cash=Decimal(config["starting_cash"]))
    health = sim.health()
    add_gate(gates, "ENVIRONMENT_OFFLINE", health.environment.value == "offline")
    add_gate(gates, "NETWORK_UNUSED", health.network_used is False)
    add_gate(gates, "BROKER_DISCONNECTED", health.connected is False)
    add_gate(gates, "ACTUAL_ORDER_COUNT_ZERO_INITIAL", sim.actual_orders_submitted == 0)

    buy = sim.submit_order(BrokerOrderRequest(
        client_order_id="v77-3-buy-1",
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("100"),
    ))
    partial = sim.apply_fill(
        buy.broker_order_id, quantity=Decimal("4"), price=Decimal("100")
    )
    add_gate(gates, "BUY_PARTIAL_STATUS", partial.status is BrokerOrderStatus.PARTIALLY_FILLED)
    add_gate(gates, "BUY_PARTIAL_QUANTITY", partial.filled_quantity == Decimal("4"))
    add_gate(gates, "BUY_PARTIAL_AVERAGE", partial.average_fill_price == Decimal("100"))
    snapshot = sim.get_account_snapshot()
    add_gate(gates, "BUY_PARTIAL_CASH_UPDATED", snapshot.cash == Decimal("99600"))
    add_gate(gates, "BUY_PARTIAL_POSITION_CREATED", snapshot.positions[0].quantity == Decimal("4"))

    filled = sim.apply_fill(
        buy.broker_order_id, quantity=Decimal("6"), price=Decimal("110")
    )
    add_gate(gates, "BUY_FULL_STATUS", filled.status is BrokerOrderStatus.FILLED)
    add_gate(gates, "BUY_FULL_QUANTITY", filled.filled_quantity == Decimal("10"))
    add_gate(gates, "BUY_WEIGHTED_AVERAGE", filled.average_fill_price == Decimal("106"))
    snapshot = sim.get_account_snapshot()
    add_gate(gates, "BUY_FULL_CASH_UPDATED", snapshot.cash == Decimal("98940"))
    add_gate(gates, "BUY_POSITION_QUANTITY", snapshot.positions[0].quantity == Decimal("10"))
    add_gate(gates, "BUY_POSITION_AVERAGE", snapshot.positions[0].average_entry_price == Decimal("106"))
    add_gate(gates, "FILLED_ORDER_NOT_OPEN", snapshot.open_orders == ())

    overfill_rejected = False
    try:
        sim.apply_fill(buy.broker_order_id, quantity=Decimal("1"), price=Decimal("120"))
    except SandboxBrokerError:
        overfill_rejected = True
    add_gate(gates, "TERMINAL_FILL_REJECTED", overfill_rejected)

    sell = sim.submit_order(BrokerOrderRequest(
        client_order_id="v77-3-sell-1",
        symbol="AAPL",
        side=OrderSide.SELL,
        quantity=Decimal("3"),
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
    ))
    sold = sim.apply_fill(
        sell.broker_order_id, quantity=Decimal("3"), price=Decimal("120")
    )
    add_gate(gates, "SELL_FULL_STATUS", sold.status is BrokerOrderStatus.FILLED)
    snapshot = sim.get_account_snapshot()
    add_gate(gates, "SELL_CASH_UPDATED", snapshot.cash == Decimal("99300"))
    add_gate(gates, "SELL_POSITION_REDUCED", snapshot.positions[0].quantity == Decimal("7"))
    add_gate(gates, "FILL_LEDGER_COUNT", sim.simulated_fill_count == 3)
    add_gate(gates, "ACTUAL_ORDER_COUNT_REMAINS_ZERO", sim.actual_orders_submitted == 0)

    event_types = [event.event_type for event in sim.event_ledger()]
    add_gate(gates, "PARTIAL_FILL_EVENT_RECORDED", "simulated_partial_fill" in event_types)
    add_gate(gates, "FULL_FILL_EVENT_RECORDED", "simulated_full_fill" in event_types)

    definition = {
        "adapter_name": sim.ADAPTER_NAME,
        "supported_transitions": [
            "accepted->partially_filled",
            "accepted->filled",
            "partially_filled->filled",
        ],
        "cash_mutation": True,
        "position_mutation": True,
        "short_positions": False,
        "actual_network_calls": 0,
        "actual_orders_submitted": 0,
    }
    lifecycle_sha = digest(definition)
    add_gate(gates, "LIFECYCLE_DIGEST_CREATED", len(lifecycle_sha) == 64)

    failed = [g["gate_id"] for g in gates if g["status"] == "FAIL"]
    status = "PASS" if not failed else "FAIL"
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "record_type": "ORDER_LIFECYCLE_SIMULATOR_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "decision": (
            "order_lifecycle_simulator_established"
            if status == "PASS" else "order_lifecycle_simulator_rejected"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
        },
        "source_anchors": {
            "v77_2_sandbox_broker_adapter_sha256": source.get("sandbox_broker_adapter_sha256"),
            "v77_2_verification_sha256": source.get("verification_sha256"),
        },
        "lifecycle_definition": definition,
        "order_lifecycle_simulator_sha256": lifecycle_sha,
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
        "simulated_orders_accepted": 2,
        "simulated_fills_created": 3,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS" else "REPAIR_V77_3_ORDER_LIFECYCLE_SIMULATOR",
    }
    result["verification_sha256"] = digest(
        {k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc"}}
    )
    return result


def summary(result: dict[str, Any]) -> dict[str, Any]:
    vr = result["verification_result"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "order_lifecycle_simulator_sha256": result["order_lifecycle_simulator_sha256"],
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
        "simulated_fills_created": result["simulated_fills_created"],
        "actual_orders_submitted": result["actual_orders_submitted"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir/"order_lifecycle_simulator_verification_v77_3.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )
    (output_dir/"order_lifecycle_simulator_summary_v77_3.json").write_text(
        json.dumps(summary(result), indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = verify(Path(args.repository_root), load_json(Path(args.config)))
    write_outputs(result, Path(args.output_dir))
    print(json.dumps(summary(result), indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
