from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "67.0"
SCHEMA_VERSION = "v67.0.paper_trade_scenarios.1"


class ScenarioError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def price(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def parse_symbols(raw: str) -> List[str]:
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    if not symbols:
        raise ScenarioError("at least one symbol is required")
    for symbol in symbols:
        if not symbol.replace(".", "").replace("-", "").isalnum():
            raise ScenarioError(f"invalid symbol: {symbol}")
    return symbols


def validate_args(trade_count: int, quantity: int, starting_price: Decimal) -> None:
    if trade_count < 1:
        raise ScenarioError("trade_count must be at least 1")
    if trade_count > 100000:
        raise ScenarioError("trade_count must not exceed 100000")
    if quantity < 1:
        raise ScenarioError("quantity must be at least 1")
    if starting_price <= 0:
        raise ScenarioError("starting_price must be positive")


def scenario_return(rng: random.Random, scenario: str, index: int) -> Decimal:
    if scenario == "winning":
        return Decimal(str(rng.uniform(0.004, 0.035)))
    if scenario == "losing":
        return Decimal(str(rng.uniform(-0.035, -0.004)))
    if scenario == "mixed":
        if index % 10 < 6:
            return Decimal(str(rng.uniform(0.003, 0.030)))
        return Decimal(str(rng.uniform(-0.025, -0.003)))
    if scenario == "volatile":
        return Decimal(str(rng.uniform(-0.060, 0.060)))
    raise ScenarioError(f"unsupported scenario: {scenario}")


def build_trade(
    rng: random.Random,
    trade_id: int,
    symbol: str,
    quantity: int,
    base_price: Decimal,
    scenario: str,
    opened_at: datetime,
) -> Dict[str, Any]:
    entry_shift = Decimal(str(rng.uniform(-0.04, 0.04)))
    entry_price = max(Decimal("1.0000"), base_price * (Decimal("1") + entry_shift))
    ret = scenario_return(rng, scenario, trade_id - 1)
    exit_price = max(Decimal("0.0100"), entry_price * (Decimal("1") + ret))

    holding_minutes = rng.randint(5, 1440)
    closed_at = opened_at + timedelta(minutes=holding_minutes)
    pnl = (exit_price - entry_price) * Decimal(quantity)

    strategy = {
        "winning": "momentum_alpha",
        "losing": "adverse_control",
        "mixed": "balanced_signal",
        "volatile": "volatility_probe",
    }[scenario]

    trade = {
        "trade_id": f"V67-{trade_id:06d}",
        "strategy": strategy,
        "symbol": symbol,
        "side": "LONG",
        "quantity": quantity,
        "entry_price": price(entry_price),
        "exit_price": price(exit_price),
        "realized_pnl": money(pnl),
        "return_pct": str((ret * Decimal("100")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
        "opened_at": opened_at.isoformat().replace("+00:00", "Z"),
        "closed_at": closed_at.isoformat().replace("+00:00", "Z"),
        "holding_minutes": holding_minutes,
        "exit_reason": "TAKE_PROFIT" if pnl > 0 else ("STOP_LOSS" if pnl < 0 else "FLAT_EXIT"),
        "status": "CLOSED",
        "network_used": False,
    }
    trade["trade_sha256"] = sha256_of(trade)
    return trade


def generate_report(
    trade_count: int,
    symbols: List[str],
    seed: int,
    scenario: str,
    quantity: int,
    starting_price: Decimal,
) -> Dict[str, Any]:
    validate_args(trade_count, quantity, starting_price)
    rng = random.Random(seed)
    start = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)

    trades: List[Dict[str, Any]] = []
    for i in range(1, trade_count + 1):
        symbol = symbols[(i - 1) % len(symbols)]
        opened_at = start + timedelta(days=i - 1, minutes=rng.randint(0, 240))
        trades.append(
            build_trade(
                rng=rng,
                trade_id=i,
                symbol=symbol,
                quantity=quantity,
                base_price=starting_price,
                scenario=scenario,
                opened_at=opened_at,
            )
        )

    wins = sum(1 for t in trades if Decimal(t["realized_pnl"]) > 0)
    losses = sum(1 for t in trades if Decimal(t["realized_pnl"]) < 0)
    flats = trade_count - wins - losses
    net_pnl = sum((Decimal(t["realized_pnl"]) for t in trades), Decimal("0"))

    report: Dict[str, Any] = {
        "status": "PASS",
        "decision": "paper_trade_scenarios_generated",
        "scenario": scenario,
        "seed": seed,
        "network_used": False,
        "approved_for_live": False,
        "trade_count": trade_count,
        "closed_trade_count": trade_count,
        "open_trade_count": 0,
        "symbols": symbols,
        "summary": {
            "win_count": wins,
            "loss_count": losses,
            "flat_count": flats,
            "net_pnl": money(net_pnl),
        },
        "trades": trades,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    report["scenario_report_sha256"] = sha256_of(report)
    return report


def run(
    output: Path,
    trade_count: int,
    symbols: List[str],
    seed: int,
    scenario: str,
    quantity: int,
    starting_price: Decimal,
) -> Dict[str, Any]:
    report = generate_report(
        trade_count=trade_count,
        symbols=symbols,
        seed=seed,
        scenario=scenario,
        quantity=quantity,
        starting_price=starting_price,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V67 Paper Trade Scenario Generator")
    parser.add_argument("--trade-count", type=int, default=100)
    parser.add_argument("--symbols", default="AAPL,MSFT,NVDA")
    parser.add_argument("--seed", type=int, default=6700)
    parser.add_argument("--scenario", choices=["winning", "losing", "mixed", "volatile"], default="mixed")
    parser.add_argument("--quantity", type=int, default=10)
    parser.add_argument("--starting-price", default="100")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        symbols = parse_symbols(args.symbols)
        starting_price = Decimal(str(args.starting_price))
        report = run(
            output=args.output,
            trade_count=args.trade_count,
            symbols=symbols,
            seed=args.seed,
            scenario=args.scenario,
            quantity=args.quantity,
            starting_price=starting_price,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "paper_trade_scenario_generation_failed",
            "error": str(exc),
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": report["status"],
        "decision": report["decision"],
        "scenario": report["scenario"],
        "trade_count": report["trade_count"],
        "closed_trade_count": report["closed_trade_count"],
        "win_count": report["summary"]["win_count"],
        "loss_count": report["summary"]["loss_count"],
        "net_pnl": report["summary"]["net_pnl"],
        "network_used": report["network_used"],
        "approved_for_live": report["approved_for_live"],
        "scenario_report_sha256": report["scenario_report_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
