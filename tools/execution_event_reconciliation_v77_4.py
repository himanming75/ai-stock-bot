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
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.execution_event_reconciliation_v77_4 import ExecutionEventReconciler
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator

VERSION = "77.4"
SCHEMA = "v77.4.execution_event_reconciliation.1"
NEXT_PHASE = "V77_5_BROKER_STATE_CHECKPOINT"


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


def git_state(root: Path) -> dict[str, str]:
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
    }


def git_is_ancestor(root: Path, ancestor: str) -> bool:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, "HEAD"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )
    if process.returncode not in {0, 1}:
        raise VerificationError(process.stderr.strip())
    return process.returncode == 0


def add_gate(gates: list[dict[str, str]], gate_id: str, passed: bool) -> None:
    gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL"})


def build_scenario() -> OrderLifecycleSimulator:
    sim = OrderLifecycleSimulator(starting_cash=Decimal("100000"))
    buy = sim.submit_order(BrokerOrderRequest(
        client_order_id="v77-4-buy",
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("100"),
    ))
    sim.apply_fill(buy.broker_order_id, quantity=Decimal("4"), price=Decimal("100"))
    sim.apply_fill(buy.broker_order_id, quantity=Decimal("6"), price=Decimal("110"))

    sell = sim.submit_order(BrokerOrderRequest(
        client_order_id="v77-4-sell",
        symbol="AAPL",
        side=OrderSide.SELL,
        quantity=Decimal("3"),
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
    ))
    sim.apply_fill(sell.broker_order_id, quantity=Decimal("3"), price=Decimal("120"))
    return sim


def verify(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    git = git_state(root)
    gates: list[dict[str, str]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_FRAMEWORK_COMMIT_IS_ANCESTOR",
             git_is_ancestor(root, config["expected_framework_commit_sha"]))

    source_path = root/"release/v77_3/output/order_lifecycle_simulator_verification_v77_3.json"
    add_gate(gates, "V77_3_VERIFICATION_EXISTS", source_path.is_file())
    source = load_json(source_path)
    add_gate(gates, "V77_3_STATUS_PASS", source.get("status") == "PASS")
    add_gate(gates, "V77_3_LIFECYCLE_ANCHOR_MATCH",
             source.get("order_lifecycle_simulator_sha256")
             == config["expected_v77_3_lifecycle_sha256"])
    add_gate(gates, "V77_3_VERIFICATION_ANCHOR_MATCH",
             source.get("verification_sha256")
             == config["expected_v77_3_verification_sha256"])
    add_gate(gates, "V77_3_NEXT_PHASE_MATCH",
             source.get("next_phase") == "V77_4_EXECUTION_EVENT_RECONCILIATION")

    sim = build_scenario()
    report = ExecutionEventReconciler().reconcile(sim)

    add_gate(gates, "RECONCILIATION_STATUS_PASS", report.passed)
    add_gate(gates, "RECONCILIATION_ISSUE_COUNT_ZERO", report.issue_count == 0)
    add_gate(gates, "CASH_RECONCILED", report.expected_cash == report.actual_cash)
    add_gate(gates, "POSITION_RECONCILED",
             dict(report.expected_positions) == dict(report.actual_positions))
    add_gate(gates, "ORDER_COUNT_CHECKED", report.checked_order_count == 2)
    add_gate(gates, "FILL_COUNT_CHECKED", report.checked_fill_count == 3)
    add_gate(gates, "EVENTS_CHECKED", report.checked_event_count == 6)
    add_gate(gates, "NETWORK_DISABLED", sim.health().network_used is False)
    add_gate(gates, "BROKER_DISCONNECTED", sim.health().connected is False)
    add_gate(gates, "ACTUAL_ORDER_COUNT_ZERO", sim.actual_orders_submitted == 0)

    definition = {
        "checks": [
            "order_fill_quantity",
            "weighted_average_fill_price",
            "cash_balance",
            "position_quantity",
            "fill_event_identity",
            "event_sequence_contiguity",
        ],
        "actual_network_calls": 0,
        "actual_orders_submitted": 0,
    }
    recon_sha = digest(definition)
    add_gate(gates, "RECONCILIATION_DIGEST_CREATED", len(recon_sha) == 64)

    failed = [g["gate_id"] for g in gates if g["status"] == "FAIL"]
    status = "PASS" if not failed else "FAIL"
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "record_type": "EXECUTION_EVENT_RECONCILIATION_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "decision": (
            "execution_event_reconciliation_established"
            if status == "PASS" else "execution_event_reconciliation_rejected"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
        },
        "source_anchors": {
            "v77_3_order_lifecycle_simulator_sha256":
                source.get("order_lifecycle_simulator_sha256"),
            "v77_3_verification_sha256": source.get("verification_sha256"),
        },
        "reconciliation_definition": definition,
        "execution_event_reconciliation_sha256": recon_sha,
        "scenario_report": report.as_dict(),
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
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS"
            else "REPAIR_V77_4_EXECUTION_EVENT_RECONCILIATION",
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
        "execution_event_reconciliation_sha256":
            result["execution_event_reconciliation_sha256"],
        "verification_sha256": result["verification_sha256"],
        **result["source_anchors"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "scenario_reconciliation_status": result["scenario_report"]["status"],
        "scenario_issue_count": result["scenario_report"]["issue_count"],
        "environment": result["environment"],
        "network_allowed": result["network_allowed"],
        "broker_connected": result["broker_connected"],
        "actual_orders_submitted": result["actual_orders_submitted"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir/"execution_event_reconciliation_verification_v77_4.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )
    (output_dir/"execution_event_reconciliation_summary_v77_4.json").write_text(
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
