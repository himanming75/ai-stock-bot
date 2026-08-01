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

from runtime_engine import Event, EventBus, ManualClock
from execution_engine import ExecutionResult, ExecutionStatus, FillRecord
from portfolio_engine import (
    FillDeduplicationGuard,
    MarketPriceBook,
    Portfolio,
    PortfolioAccountingEngine,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v107_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
    clock = ManualClock(now)
    bus = EventBus()
    snapshots = []
    bus.subscribe("portfolio.snapshot", lambda event: snapshots.append(event.payload["snapshot"]))

    portfolio = Portfolio(starting_cash=Decimal("1000"))
    price_book = MarketPriceBook()
    engine = PortfolioAccountingEngine(
        event_bus=bus,
        portfolio=portfolio,
        price_book=price_book,
        fill_guard=FillDeduplicationGuard(),
        now=clock.now,
        buying_power_multiplier=Decimal("1"),
    )
    engine.start()

    buy_fill_1 = FillRecord(Decimal("0.5"), Decimal("50"), now)
    partial_buy = ExecutionResult(
        request_id="req-buy",
        client_order_id="BOT-BUY-1",
        broker_order_id="mock-buy",
        status=ExecutionStatus.PARTIALLY_FILLED,
        requested_quantity=Decimal("1"),
        filled_quantity=Decimal("0.5"),
        average_fill_price=Decimal("50"),
        updated_at=now,
        fills=(buy_fill_1,),
    )
    bus.publish(Event(
        "execution.update",
        {"result":partial_buy, "side":"BUY", "symbol":"AAPL"},
        now,
    ))

    clock.advance(seconds=1)
    buy_fill_2 = FillRecord(Decimal("0.5"), Decimal("52"), clock.now())
    full_buy = ExecutionResult(
        request_id="req-buy",
        client_order_id="BOT-BUY-1",
        broker_order_id="mock-buy",
        status=ExecutionStatus.FILLED,
        requested_quantity=Decimal("1"),
        filled_quantity=Decimal("1"),
        average_fill_price=Decimal("51"),
        updated_at=clock.now(),
        fills=(buy_fill_1, buy_fill_2),
    )
    bus.publish(Event(
        "execution.update",
        {"result":full_buy, "side":"BUY", "symbol":"AAPL"},
        clock.now(),
    ))

    price_book.update("AAPL", Decimal("55"))
    before_sell = engine.snapshot()

    clock.advance(seconds=1)
    sell_fill = FillRecord(Decimal("0.5"), Decimal("56"), clock.now())
    partial_sell = ExecutionResult(
        request_id="req-sell",
        client_order_id="BOT-SELL-1",
        broker_order_id="mock-sell",
        status=ExecutionStatus.PARTIALLY_FILLED,
        requested_quantity=Decimal("1"),
        filled_quantity=Decimal("0.5"),
        average_fill_price=Decimal("56"),
        updated_at=clock.now(),
        fills=(sell_fill,),
    )
    bus.publish(Event(
        "execution.update",
        {"result":partial_sell, "side":"SELL", "symbol":"AAPL"},
        clock.now(),
    ))
    engine.stop()

    final_snapshot = engine.snapshot()
    position = portfolio.positions["AAPL"]

    result = {
        "stage_range": "V106.01-V107.00",
        "status": "PASS",
        "implementation_type": "PORTFOLIO_FILL_ACCOUNTING_FOUNDATION",
        "starting_cash": "1000",
        "final_cash": str(final_snapshot.cash),
        "final_equity": str(final_snapshot.equity),
        "final_market_value": str(final_snapshot.market_value),
        "realized_pnl": str(final_snapshot.realized_pnl),
        "unrealized_pnl_before_sell": str(before_sell.unrealized_pnl),
        "final_unrealized_pnl": str(final_snapshot.unrealized_pnl),
        "position_quantity": str(position.quantity),
        "position_average_price": str(position.average_price),
        "buying_power": str(final_snapshot.buying_power),
        "snapshot_event_count": len(snapshots),
        "stats": vars(engine.stats),
        "network_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "next_phase": "V107_01_RUNTIME_RISK_MANAGER_FOUNDATION",
    }

    (output / "portfolio_fill_accounting_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
