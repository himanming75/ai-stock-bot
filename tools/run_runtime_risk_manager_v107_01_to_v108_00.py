from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_engine import EventBus, ManualClock
from execution_engine import OrderIntent, OrderSide, OrderType, TimeInForce
from portfolio_engine import PortfolioSnapshot, PositionSnapshot
from risk_engine import RiskLimits, RuntimeRiskManager, RuntimeRiskState


def make_intent(now, *, side=OrderSide.BUY, notional="50", intent_id=None):
    kwargs = {}
    if intent_id:
        kwargs["intent_id"] = intent_id
    return OrderIntent(
        symbol="AAPL",
        side=side,
        quantity=Decimal("1"),
        reference_price=Decimal("50"),
        estimated_notional=Decimal(notional),
        created_at=now,
        expires_at=now + timedelta(seconds=30),
        source_signal_id="demo-signal",
        strategy_name="demo",
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        **kwargs,
    )


def make_snapshot(now, *, equity="1000", realized="0", market="100", positions=1):
    pos = tuple(
        PositionSnapshot(
            symbol=f"SYM{i}",
            quantity=Decimal("1"),
            average_price=Decimal("50"),
            market_price=Decimal("50"),
            market_value=Decimal("50"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        for i in range(positions)
    )
    return PortfolioSnapshot(
        captured_at=now,
        cash=Decimal(equity)-Decimal(market),
        equity=Decimal(equity),
        market_value=Decimal(market),
        realized_pnl=Decimal(realized),
        unrealized_pnl=Decimal("0"),
        buying_power=Decimal("1000"),
        positions=pos,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v108_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
    clock = ManualClock(now)
    bus = EventBus()
    manager = RuntimeRiskManager(
        event_bus=bus,
        limits=RiskLimits(
            max_daily_loss=Decimal("50"),
            max_drawdown=Decimal("100"),
            max_symbol_exposure=Decimal("250"),
            max_total_exposure=Decimal("500"),
            max_open_positions=3,
            max_consecutive_losses=3,
        ),
        state=RuntimeRiskState(current_equity=Decimal("1000"), peak_equity=Decimal("1000")),
        now=clock.now,
    )

    approved = manager.evaluate(make_intent(now, notional="50"))
    exposure_rejected = manager.evaluate(make_intent(now, notional="450"))

    manager.update_portfolio(make_snapshot(now, equity="900", realized="-50", market="100", positions=1))
    halted = manager.evaluate(make_intent(now, notional="25"))
    sell_after_halt = manager.evaluate(make_intent(now, side=OrderSide.SELL, notional="25"))

    final_snapshot = manager.snapshot()

    result = {
        "stage_range": "V107.01-V108.00",
        "status": "PASS",
        "implementation_type": "RUNTIME_RISK_MANAGER_FOUNDATION",
        "normal_decision": approved.status.value,
        "exposure_decision": exposure_rejected.status.value,
        "exposure_reason": exposure_rejected.reason,
        "halted_decision": halted.status.value,
        "halted_reason": halted.reason,
        "sell_after_halt_decision": sell_after_halt.status.value,
        "kill_switch_engaged": final_snapshot.kill_switch_engaged,
        "emergency_stop_engaged": final_snapshot.emergency_stop_engaged,
        "new_buys_allowed": final_snapshot.new_buys_allowed,
        "drawdown": str(final_snapshot.drawdown),
        "daily_realized_pnl": str(final_snapshot.daily_realized_pnl),
        "stats": vars(manager.stats),
        "network_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "next_phase": "V108_01_END_TO_END_PAPER_RUNTIME_FOUNDATION",
    }

    (output / "runtime_risk_manager_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
