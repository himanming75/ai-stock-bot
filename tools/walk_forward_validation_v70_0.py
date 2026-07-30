from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


VERSION = "70.0"
SCHEMA_VERSION = "v70.0.walk_forward_validation.1"
SUPPORTED_INPUT_SCHEMA = "v67.0.paper_trade_scenarios.1"


class WalkForwardError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def dec(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise WalkForwardError(f"{field} must be numeric") from exc


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WalkForwardError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WalkForwardError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise WalkForwardError("top-level JSON must be an object")
    return data


def validate_report(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise WalkForwardError("input status must be PASS")
    if report.get("schema_version") != SUPPORTED_INPUT_SCHEMA:
        raise WalkForwardError("unsupported input schema_version")
    if report.get("network_used") is not False:
        raise WalkForwardError("network_used must be false")
    if report.get("approved_for_live") is not False:
        raise WalkForwardError("approved_for_live must be false")

    trades = report.get("trades")
    if not isinstance(trades, list):
        raise WalkForwardError("trades must be a list")
    if report.get("trade_count") != len(trades):
        raise WalkForwardError("trade_count mismatch")
    if report.get("closed_trade_count") != len(trades):
        raise WalkForwardError("closed_trade_count mismatch")
    if report.get("open_trade_count") != 0:
        raise WalkForwardError("open_trade_count must be zero")

    required = {
        "trade_id", "strategy", "symbol", "realized_pnl",
        "opened_at", "closed_at", "holding_minutes", "status",
        "network_used",
    }
    for index, trade in enumerate(trades):
        if not isinstance(trade, dict):
            raise WalkForwardError(f"trade {index} must be an object")
        missing = required - set(trade)
        if missing:
            raise WalkForwardError(f"trade {index} missing fields: {sorted(missing)}")
        if trade["status"] != "CLOSED":
            raise WalkForwardError(f"trade {index} must be CLOSED")
        if trade["network_used"] is not False:
            raise WalkForwardError(f"trade {index} network_used must be false")


def sort_trades(trades: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        trades,
        key=lambda t: (
            str(t["opened_at"]),
            str(t["closed_at"]),
            str(t["trade_id"]),
        ),
    )


def metrics(trades: Sequence[Dict[str, Any]], label: str) -> Dict[str, Any]:
    pnls = [dec(t["realized_pnl"], "realized_pnl") for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    flats = [x for x in pnls if x == 0]
    total = len(pnls)

    gross_profit = sum(wins, Decimal("0"))
    gross_loss = abs(sum(losses, Decimal("0")))
    net_pnl = sum(pnls, Decimal("0"))
    win_rate = Decimal(len(wins)) / Decimal(total) if total else Decimal("0")
    expectancy = net_pnl / Decimal(total) if total else Decimal("0")
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (Decimal("999999") if gross_profit > 0 else Decimal("0"))
    )

    result = {
        "label": label,
        "trade_count": total,
        "win_count": len(wins),
        "loss_count": len(losses),
        "flat_count": len(flats),
        "gross_profit": f"{gross_profit:.4f}",
        "gross_loss": f"{gross_loss:.4f}",
        "net_pnl": f"{net_pnl:.4f}",
        "win_rate": f"{win_rate:.6f}",
        "profit_factor": f"{profit_factor:.6f}",
        "expectancy": f"{expectancy:.4f}",
    }
    result["metrics_sha256"] = sha256_of(result)
    return result


def split_windows(
    trades: Sequence[Dict[str, Any]],
    train_size: int,
    forward_size: int,
    step_size: int,
) -> List[Dict[str, Any]]:
    if train_size < 1:
        raise WalkForwardError("train_size must be at least 1")
    if forward_size < 1:
        raise WalkForwardError("forward_size must be at least 1")
    if step_size < 1:
        raise WalkForwardError("step_size must be at least 1")

    ordered = sort_trades(trades)
    windows: List[Dict[str, Any]] = []
    start = 0
    number = 1

    while start + train_size + forward_size <= len(ordered):
        train = ordered[start:start + train_size]
        forward = ordered[start + train_size:start + train_size + forward_size]
        windows.append({
            "window": number,
            "train_start_index": start,
            "train_end_index": start + train_size - 1,
            "forward_start_index": start + train_size,
            "forward_end_index": start + train_size + forward_size - 1,
            "train_first_trade_id": train[0]["trade_id"],
            "train_last_trade_id": train[-1]["trade_id"],
            "forward_first_trade_id": forward[0]["trade_id"],
            "forward_last_trade_id": forward[-1]["trade_id"],
            "train_metrics": metrics(train, f"window_{number}_train"),
            "forward_metrics": metrics(forward, f"window_{number}_forward"),
        })
        start += step_size
        number += 1

    if not windows:
        raise WalkForwardError(
            "not enough trades for one complete train/forward window"
        )
    return windows


def evaluate_window(
    window: Dict[str, Any],
    minimum_forward_win_rate: Decimal,
    minimum_forward_profit_factor: Decimal,
    minimum_forward_expectancy: Decimal,
    minimum_expectancy_retention: Decimal,
) -> Dict[str, Any]:
    train = window["train_metrics"]
    forward = window["forward_metrics"]

    train_expectancy = dec(train["expectancy"], "train expectancy")
    forward_expectancy = dec(forward["expectancy"], "forward expectancy")
    forward_win_rate = dec(forward["win_rate"], "forward win_rate")
    forward_profit_factor = dec(forward["profit_factor"], "forward profit factor")

    if train_expectancy > 0:
        retention = forward_expectancy / train_expectancy
    elif forward_expectancy >= 0:
        retention = Decimal("1")
    else:
        retention = Decimal("-1")

    checks = {
        "forward_win_rate": forward_win_rate >= minimum_forward_win_rate,
        "forward_profit_factor": forward_profit_factor >= minimum_forward_profit_factor,
        "forward_expectancy": forward_expectancy > minimum_forward_expectancy,
        "expectancy_retention": retention >= minimum_expectancy_retention,
    }
    passed = all(checks.values())

    result = dict(window)
    result["expectancy_retention"] = f"{retention:.6f}"
    result["checks"] = checks
    result["window_status"] = "PASS" if passed else "FAIL"
    result["window_sha256"] = sha256_of(result)
    return result


def build_validation(
    report: Dict[str, Any],
    champion_strategy: Optional[str] = None,
    train_size: int = 50,
    forward_size: int = 20,
    step_size: int = 10,
    minimum_forward_win_rate: Decimal = Decimal("0.45"),
    minimum_forward_profit_factor: Decimal = Decimal("1.00"),
    minimum_forward_expectancy: Decimal = Decimal("0"),
    minimum_expectancy_retention: Decimal = Decimal("0.25"),
    minimum_pass_rate: Decimal = Decimal("0.60"),
) -> Dict[str, Any]:
    validate_report(report)

    trades = report["trades"]
    detected = sorted({str(t["strategy"]) for t in trades})
    if champion_strategy is None:
        if len(detected) != 1:
            raise WalkForwardError(
                "champion_strategy is required when multiple strategies exist"
            )
        champion_strategy = detected[0]

    selected = [t for t in trades if str(t["strategy"]) == champion_strategy]
    if not selected:
        raise WalkForwardError(
            f"no trades found for champion_strategy: {champion_strategy}"
        )

    raw_windows = split_windows(selected, train_size, forward_size, step_size)
    evaluated = [
        evaluate_window(
            window,
            minimum_forward_win_rate,
            minimum_forward_profit_factor,
            minimum_forward_expectancy,
            minimum_expectancy_retention,
        )
        for window in raw_windows
    ]

    pass_count = sum(1 for w in evaluated if w["window_status"] == "PASS")
    fail_count = len(evaluated) - pass_count
    pass_rate = Decimal(pass_count) / Decimal(len(evaluated))

    all_forward_trades: List[Dict[str, Any]] = []
    ordered = sort_trades(selected)
    for window in evaluated:
        start = window["forward_start_index"]
        end = window["forward_end_index"] + 1
        all_forward_trades.extend(ordered[start:end])

    aggregate_forward = metrics(all_forward_trades, "aggregate_forward")
    approved = pass_rate >= minimum_pass_rate

    result = {
        "status": "PASS",
        "decision": (
            "walk_forward_validation_approved"
            if approved
            else "walk_forward_validation_rejected"
        ),
        "validation_state": "APPROVED" if approved else "REJECTED",
        "champion_strategy": champion_strategy,
        "detected_strategies": detected,
        "selected_trade_count": len(selected),
        "window_count": len(evaluated),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": f"{pass_rate:.6f}",
        "aggregate_forward_metrics": aggregate_forward,
        "windows": evaluated,
        "configuration": {
            "train_size": train_size,
            "forward_size": forward_size,
            "step_size": step_size,
            "minimum_forward_win_rate": f"{minimum_forward_win_rate:.6f}",
            "minimum_forward_profit_factor": f"{minimum_forward_profit_factor:.6f}",
            "minimum_forward_expectancy": f"{minimum_forward_expectancy:.6f}",
            "minimum_expectancy_retention": f"{minimum_expectancy_retention:.6f}",
            "minimum_pass_rate": f"{minimum_pass_rate:.6f}",
        },
        "requires_monte_carlo_validation": approved,
        "approved_for_live": False,
        "network_used": False,
        "source_scenario_report_sha256": report.get("scenario_report_sha256"),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["walk_forward_report_sha256"] = sha256_of(result)
    return result


def run(
    input_path: Path,
    output_path: Path,
    champion_strategy: Optional[str],
    train_size: int,
    forward_size: int,
    step_size: int,
    minimum_pass_rate: Decimal,
) -> Dict[str, Any]:
    report = read_json(input_path)
    result = build_validation(
        report=report,
        champion_strategy=champion_strategy,
        train_size=train_size,
        forward_size=forward_size,
        step_size=step_size,
        minimum_pass_rate=minimum_pass_rate,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V70 Walk-Forward Validation")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--champion-strategy")
    parser.add_argument("--train-size", type=int, default=50)
    parser.add_argument("--forward-size", type=int, default=20)
    parser.add_argument("--step-size", type=int, default=10)
    parser.add_argument("--minimum-pass-rate", type=Decimal, default=Decimal("0.60"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        result = run(
            input_path=args.input,
            output_path=args.output,
            champion_strategy=args.champion_strategy,
            train_size=args.train_size,
            forward_size=args.forward_size,
            step_size=args.step_size,
            minimum_pass_rate=args.minimum_pass_rate,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "walk_forward_validation_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "validation_state": result["validation_state"],
        "champion_strategy": result["champion_strategy"],
        "selected_trade_count": result["selected_trade_count"],
        "window_count": result["window_count"],
        "pass_count": result["pass_count"],
        "fail_count": result["fail_count"],
        "pass_rate": result["pass_rate"],
        "aggregate_forward_win_rate": result["aggregate_forward_metrics"]["win_rate"],
        "aggregate_forward_profit_factor": result["aggregate_forward_metrics"]["profit_factor"],
        "aggregate_forward_expectancy": result["aggregate_forward_metrics"]["expectancy"],
        "requires_monte_carlo_validation": result["requires_monte_carlo_validation"],
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "walk_forward_report_sha256": result["walk_forward_report_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
