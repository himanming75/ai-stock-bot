from __future__ import annotations

import argparse
import hashlib
import json
import random
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "69.1"
SCHEMA_VERSION = "v69.1.multi_strategy_scenario_builder.1"
V67_SCHEMA_VERSION = "v67.0.paper_trade_scenarios.1"


class ScenarioBuilderError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def q4(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.0001')):.4f}"


def q6(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


STRATEGY_PROFILES: Dict[str, Dict[str, Any]] = {
    "momentum": {
        "win_probability": 0.58,
        "win_return_range": (0.009, 0.030),
        "loss_return_range": (-0.022, -0.006),
        "holding_minutes": (45, 720),
        "exit_win": "TAKE_PROFIT",
        "exit_loss": "TRAILING_STOP",
    },
    "mean_reversion": {
        "win_probability": 0.64,
        "win_return_range": (0.005, 0.018),
        "loss_return_range": (-0.020, -0.005),
        "holding_minutes": (30, 480),
        "exit_win": "MEAN_REVERSION_TARGET",
        "exit_loss": "STOP_LOSS",
    },
    "breakout": {
        "win_probability": 0.46,
        "win_return_range": (0.018, 0.045),
        "loss_return_range": (-0.018, -0.006),
        "holding_minutes": (60, 960),
        "exit_win": "BREAKOUT_TARGET",
        "exit_loss": "FALSE_BREAKOUT_STOP",
    },
}


def parse_symbols(raw: str) -> List[str]:
    symbols = [item.strip().upper() for item in raw.split(",") if item.strip()]
    if not symbols:
        raise ScenarioBuilderError("at least one symbol is required")
    if len(set(symbols)) != len(symbols):
        raise ScenarioBuilderError("symbols must be unique")
    return symbols


def validate_strategy_names(strategies: List[str]) -> None:
    if not strategies:
        raise ScenarioBuilderError("at least one strategy is required")
    unknown = [s for s in strategies if s not in STRATEGY_PROFILES]
    if unknown:
        raise ScenarioBuilderError(f"unsupported strategies: {', '.join(unknown)}")
    if len(set(strategies)) != len(strategies):
        raise ScenarioBuilderError("strategies must be unique")


def build_trade(
    rng: random.Random,
    strategy: str,
    symbol: str,
    trade_number: int,
    quantity: int,
    starting_price: Decimal,
) -> Dict[str, Any]:
    profile = STRATEGY_PROFILES[strategy]
    won = rng.random() < profile["win_probability"]

    if won:
        return_rate = Decimal(str(rng.uniform(*profile["win_return_range"])))
        exit_reason = profile["exit_win"]
    else:
        return_rate = Decimal(str(rng.uniform(*profile["loss_return_range"])))
        exit_reason = profile["exit_loss"]

    drift = Decimal(str(rng.uniform(-0.04, 0.04)))
    entry_price = starting_price * (Decimal("1") + drift)
    exit_price = entry_price * (Decimal("1") + return_rate)
    realized_pnl = (exit_price - entry_price) * Decimal(quantity)

    day = 1 + ((trade_number - 1) % 28)
    month = 1 + (((trade_number - 1) // 28) % 6)
    opened_hour = 14 + (trade_number % 5)
    holding_minutes = rng.randint(*profile["holding_minutes"])
    opened_at = f"2026-{month:02d}-{day:02d}T{opened_hour:02d}:00:00Z"

    total_minutes = opened_hour * 60 + holding_minutes
    close_day = day + total_minutes // (24 * 60)
    close_hour = (total_minutes // 60) % 24
    close_minute = total_minutes % 60
    close_month = month
    while close_day > 28:
        close_day -= 28
        close_month += 1
        if close_month > 12:
            close_month = 1
    closed_at = f"2026-{close_month:02d}-{close_day:02d}T{close_hour:02d}:{close_minute:02d}:00Z"

    trade = {
        "trade_id": f"V69-1-{strategy.upper()}-{trade_number:06d}",
        "strategy": strategy,
        "symbol": symbol,
        "side": "LONG",
        "quantity": quantity,
        "entry_price": q4(entry_price),
        "exit_price": q4(exit_price),
        "realized_pnl": q4(realized_pnl),
        "return_pct": q6(return_rate * Decimal("100")),
        "opened_at": opened_at,
        "closed_at": closed_at,
        "holding_minutes": holding_minutes,
        "exit_reason": exit_reason,
        "status": "CLOSED",
        "network_used": False,
    }
    trade["trade_sha256"] = sha256_of(trade)
    return trade


def summarize(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    pnls = [Decimal(t["realized_pnl"]) for t in trades]
    wins = sum(1 for x in pnls if x > 0)
    losses = sum(1 for x in pnls if x < 0)
    flats = len(pnls) - wins - losses
    return {
        "win_count": wins,
        "loss_count": losses,
        "flat_count": flats,
        "net_pnl": q4(sum(pnls, Decimal("0"))),
    }


def build_v67_report(
    strategy: str,
    trade_count: int,
    symbols: List[str],
    seed: int,
    quantity: int,
    starting_price: Decimal,
) -> Dict[str, Any]:
    if trade_count < 1:
        raise ScenarioBuilderError("trade_count must be at least 1")
    if quantity < 1:
        raise ScenarioBuilderError("quantity must be at least 1")
    if starting_price <= 0:
        raise ScenarioBuilderError("starting_price must be positive")

    rng = random.Random(seed)
    trades = [
        build_trade(
            rng=rng,
            strategy=strategy,
            symbol=symbols[(i - 1) % len(symbols)],
            trade_number=i,
            quantity=quantity,
            starting_price=starting_price,
        )
        for i in range(1, trade_count + 1)
    ]

    report = {
        "status": "PASS",
        "decision": "paper_trade_scenarios_generated",
        "scenario": f"strategy_profile_{strategy}",
        "strategy": strategy,
        "seed": seed,
        "network_used": False,
        "approved_for_live": False,
        "trade_count": trade_count,
        "closed_trade_count": trade_count,
        "open_trade_count": 0,
        "symbols": symbols,
        "summary": summarize(trades),
        "trades": trades,
        "schema_version": V67_SCHEMA_VERSION,
        "version": "67.0",
        "generated_by": "v69.1.multi_strategy_scenario_builder",
    }
    report["scenario_report_sha256"] = sha256_of(report)
    return report


def build_bundle(
    strategies: List[str],
    trade_count: int = 100,
    symbols: Optional[List[str]] = None,
    seed: int = 6910,
    quantity: int = 10,
    starting_price: Decimal = Decimal("100"),
) -> Dict[str, Any]:
    validate_strategy_names(strategies)
    symbols = symbols or ["AAPL", "MSFT", "NVDA"]

    reports = {}
    summaries = []
    for index, strategy in enumerate(strategies):
        strategy_seed = seed + (index * 1000)
        report = build_v67_report(
            strategy=strategy,
            trade_count=trade_count,
            symbols=symbols,
            seed=strategy_seed,
            quantity=quantity,
            starting_price=starting_price,
        )
        reports[strategy] = report
        summaries.append({
            "strategy": strategy,
            "seed": strategy_seed,
            "trade_count": report["trade_count"],
            "win_count": report["summary"]["win_count"],
            "loss_count": report["summary"]["loss_count"],
            "net_pnl": report["summary"]["net_pnl"],
            "scenario_report_sha256": report["scenario_report_sha256"],
        })

    bundle = {
        "status": "PASS",
        "decision": "multi_strategy_scenarios_built",
        "strategy_count": len(strategies),
        "strategies": strategies,
        "trade_count_per_strategy": trade_count,
        "total_trade_count": trade_count * len(strategies),
        "summaries": summaries,
        "reports": reports,
        "network_used": False,
        "approved_for_live": False,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    bundle["bundle_sha256"] = sha256_of(bundle)
    return bundle


def write_bundle(bundle: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, Path] = {}

    for strategy, report in bundle["reports"].items():
        path = output_dir / f"paper_trade_scenarios_{strategy}_v69_1.json"
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[strategy] = path

    manifest = dict(bundle)
    manifest["reports"] = {
        strategy: str(path)
        for strategy, path in written.items()
    }
    manifest_path = output_dir / "multi_strategy_scenario_manifest_v69_1.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written["manifest"] = manifest_path
    return written


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V69.1 Multi-Strategy Scenario Builder")
    parser.add_argument(
        "--strategies",
        default="momentum,mean_reversion,breakout",
        help="Comma-separated strategy names",
    )
    parser.add_argument("--trade-count", type=int, default=100)
    parser.add_argument("--symbols", default="AAPL,MSFT,NVDA")
    parser.add_argument("--seed", type=int, default=6910)
    parser.add_argument("--quantity", type=int, default=10)
    parser.add_argument("--starting-price", type=Decimal, default=Decimal("100"))
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
        symbols = parse_symbols(args.symbols)
        bundle = build_bundle(
            strategies=strategies,
            trade_count=args.trade_count,
            symbols=symbols,
            seed=args.seed,
            quantity=args.quantity,
            starting_price=args.starting_price,
        )
        written = write_bundle(bundle, args.output_dir)
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "multi_strategy_scenario_build_failed",
            "error": str(exc),
            "network_used": False,
            "approved_for_live": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": bundle["status"],
        "decision": bundle["decision"],
        "strategy_count": bundle["strategy_count"],
        "trade_count_per_strategy": bundle["trade_count_per_strategy"],
        "total_trade_count": bundle["total_trade_count"],
        "summaries": bundle["summaries"],
        "manifest": str(written["manifest"]),
        "network_used": False,
        "approved_for_live": False,
        "bundle_sha256": bundle["bundle_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
