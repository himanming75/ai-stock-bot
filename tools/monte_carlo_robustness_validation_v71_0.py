from __future__ import annotations

import argparse
import hashlib
import json
import random
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


VERSION = "71.0"
SCHEMA_VERSION = "v71.0.monte_carlo_robustness_validation.1"
SUPPORTED_WALK_FORWARD_SCHEMA = "v70.0.walk_forward_validation.1"
SUPPORTED_TRADE_SCHEMA = "v67.0.paper_trade_scenarios.1"


class MonteCarloError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def dec(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MonteCarloError(f"{field} must be numeric") from exc


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MonteCarloError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MonteCarloError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise MonteCarloError("top-level JSON must be an object")
    return data


def validate_walk_forward(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise MonteCarloError("walk-forward status must be PASS")
    if report.get("schema_version") != SUPPORTED_WALK_FORWARD_SCHEMA:
        raise MonteCarloError("unsupported walk-forward schema_version")
    if report.get("network_used") is not False:
        raise MonteCarloError("walk-forward network_used must be false")
    if report.get("approved_for_live") is not False:
        raise MonteCarloError("walk-forward approved_for_live must be false")


def validate_trade_report(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise MonteCarloError("trade report status must be PASS")
    if report.get("schema_version") != SUPPORTED_TRADE_SCHEMA:
        raise MonteCarloError("unsupported trade schema_version")
    if report.get("network_used") is not False:
        raise MonteCarloError("trade report network_used must be false")
    if report.get("approved_for_live") is not False:
        raise MonteCarloError("trade report approved_for_live must be false")

    trades = report.get("trades")
    if not isinstance(trades, list) or not trades:
        raise MonteCarloError("trades must be a non-empty list")
    if report.get("trade_count") != len(trades):
        raise MonteCarloError("trade_count mismatch")

    for index, trade in enumerate(trades):
        if not isinstance(trade, dict):
            raise MonteCarloError(f"trade {index} must be an object")
        for field in ("trade_id", "strategy", "realized_pnl", "status", "network_used"):
            if field not in trade:
                raise MonteCarloError(f"trade {index} missing field: {field}")
        if trade["status"] != "CLOSED":
            raise MonteCarloError(f"trade {index} must be CLOSED")
        if trade["network_used"] is not False:
            raise MonteCarloError(f"trade {index} network_used must be false")


def drawdown_stats(pnls: Sequence[Decimal]) -> Dict[str, Decimal]:
    equity = Decimal("0")
    peak = Decimal("0")
    max_drawdown = Decimal("0")
    max_drawdown_pct = Decimal("0")

    for pnl in pnls:
        equity += pnl
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        if peak > 0:
            pct = drawdown / peak
            if pct > max_drawdown_pct:
                max_drawdown_pct = pct

    return {
        "ending_equity": equity,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
    }


def percentile(sorted_values: Sequence[Decimal], q: Decimal) -> Decimal:
    if not sorted_values:
        return Decimal("0")
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]

    position = q * Decimal(len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - Decimal(lower)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def build_blocked_result(
    walk_forward: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    result = {
        "status": "PASS",
        "decision": "monte_carlo_validation_blocked",
        "validation_state": "BLOCKED",
        "block_reason": reason,
        "champion_strategy": walk_forward.get("champion_strategy"),
        "walk_forward_state": walk_forward.get("validation_state"),
        "simulation_count": 0,
        "requires_strategy_revision": True,
        "requires_extended_paper_validation": False,
        "approved_for_live": False,
        "network_used": False,
        "source_walk_forward_report_sha256": walk_forward.get(
            "walk_forward_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["monte_carlo_report_sha256"] = sha256_of(result)
    return result


def run_simulations(
    pnls: Sequence[Decimal],
    simulation_count: int,
    seed: int,
) -> List[Dict[str, Decimal]]:
    if simulation_count < 100:
        raise MonteCarloError("simulation_count must be at least 100")

    rng = random.Random(seed)
    simulations: List[Dict[str, Decimal]] = []

    for _ in range(simulation_count):
        shuffled = list(pnls)
        rng.shuffle(shuffled)
        stats = drawdown_stats(shuffled)
        stats["net_pnl"] = sum(shuffled, Decimal("0"))
        simulations.append(stats)

    return simulations


def build_validation(
    walk_forward: Dict[str, Any],
    trade_report: Dict[str, Any],
    simulation_count: int = 1000,
    seed: int = 7100,
    maximum_p95_drawdown_pct: Decimal = Decimal("0.50"),
    minimum_profitable_simulation_rate: Decimal = Decimal("0.95"),
) -> Dict[str, Any]:
    validate_walk_forward(walk_forward)

    if (
        walk_forward.get("validation_state") != "APPROVED"
        or walk_forward.get("requires_monte_carlo_validation") is not True
    ):
        return build_blocked_result(
            walk_forward,
            "walk-forward validation did not approve Monte Carlo progression",
        )

    validate_trade_report(trade_report)

    champion = walk_forward.get("champion_strategy")
    selected = [
        t for t in trade_report["trades"]
        if str(t["strategy"]) == str(champion)
    ]
    if not selected:
        raise MonteCarloError(f"no trades found for champion strategy: {champion}")

    pnls = [dec(t["realized_pnl"], "realized_pnl") for t in selected]
    simulations = run_simulations(pnls, simulation_count, seed)

    net_pnls = sorted(s["net_pnl"] for s in simulations)
    drawdowns = sorted(s["max_drawdown"] for s in simulations)
    drawdown_pcts = sorted(s["max_drawdown_pct"] for s in simulations)
    profitable_count = sum(1 for s in simulations if s["net_pnl"] > 0)
    profitable_rate = Decimal(profitable_count) / Decimal(simulation_count)

    p05_net_pnl = percentile(net_pnls, Decimal("0.05"))
    p50_net_pnl = percentile(net_pnls, Decimal("0.50"))
    p95_drawdown = percentile(drawdowns, Decimal("0.95"))
    p95_drawdown_pct = percentile(drawdown_pcts, Decimal("0.95"))

    checks = {
        "profitable_simulation_rate": (
            profitable_rate >= minimum_profitable_simulation_rate
        ),
        "p05_net_pnl_positive": p05_net_pnl > 0,
        "p95_drawdown_pct": (
            p95_drawdown_pct <= maximum_p95_drawdown_pct
        ),
    }
    approved = all(checks.values())

    result = {
        "status": "PASS",
        "decision": (
            "monte_carlo_robustness_approved"
            if approved
            else "monte_carlo_robustness_rejected"
        ),
        "validation_state": "APPROVED" if approved else "REJECTED",
        "champion_strategy": champion,
        "selected_trade_count": len(selected),
        "simulation_count": simulation_count,
        "seed": seed,
        "profitable_simulation_count": profitable_count,
        "profitable_simulation_rate": f"{profitable_rate:.6f}",
        "p05_net_pnl": f"{p05_net_pnl:.4f}",
        "p50_net_pnl": f"{p50_net_pnl:.4f}",
        "p95_max_drawdown": f"{p95_drawdown:.4f}",
        "p95_max_drawdown_pct": f"{p95_drawdown_pct:.6f}",
        "checks": checks,
        "configuration": {
            "maximum_p95_drawdown_pct": f"{maximum_p95_drawdown_pct:.6f}",
            "minimum_profitable_simulation_rate": (
                f"{minimum_profitable_simulation_rate:.6f}"
            ),
        },
        "requires_extended_paper_validation": approved,
        "requires_strategy_revision": not approved,
        "approved_for_live": False,
        "network_used": False,
        "source_walk_forward_report_sha256": walk_forward.get(
            "walk_forward_report_sha256"
        ),
        "source_trade_report_sha256": trade_report.get(
            "scenario_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["monte_carlo_report_sha256"] = sha256_of(result)
    return result


def run(
    walk_forward_path: Path,
    trade_report_path: Path,
    output_path: Path,
    simulation_count: int,
    seed: int,
) -> Dict[str, Any]:
    walk_forward = read_json(walk_forward_path)
    trade_report = read_json(trade_report_path)

    result = build_validation(
        walk_forward=walk_forward,
        trade_report=trade_report,
        simulation_count=simulation_count,
        seed=seed,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V71 Monte Carlo Robustness Validation"
    )
    parser.add_argument("--walk-forward", required=True, type=Path)
    parser.add_argument("--paper-trades", required=True, type=Path)
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7100)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        result = run(
            walk_forward_path=args.walk_forward,
            trade_report_path=args.paper_trades,
            output_path=args.output,
            simulation_count=args.simulations,
            seed=args.seed,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "monte_carlo_validation_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    summary = {
        "status": result["status"],
        "decision": result["decision"],
        "validation_state": result["validation_state"],
        "champion_strategy": result.get("champion_strategy"),
        "simulation_count": result["simulation_count"],
        "requires_extended_paper_validation": result.get(
            "requires_extended_paper_validation"
        ),
        "requires_strategy_revision": result.get(
            "requires_strategy_revision"
        ),
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "monte_carlo_report_sha256": result[
            "monte_carlo_report_sha256"
        ],
    }

    for field in (
        "block_reason",
        "selected_trade_count",
        "profitable_simulation_rate",
        "p05_net_pnl",
        "p50_net_pnl",
        "p95_max_drawdown",
        "p95_max_drawdown_pct",
    ):
        if field in result:
            summary[field] = result[field]

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
