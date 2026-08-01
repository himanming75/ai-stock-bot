from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from runtime_engine import Event, EventBus, ManualClock
from execution_engine import (
    ExecutionResult,
    ExecutionStatus,
    FillRecord,
)
from portfolio_engine import (
    FillDeduplicationGuard,
    MarketPriceBook,
    Portfolio,
    PortfolioAccountingEngine,
    TradeSide,
)


class PortfolioFillAccountingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)

    def engine(self, cash="1000"):
        bus = EventBus()
        clock = ManualClock(self.now)
        portfolio = Portfolio(starting_cash=Decimal(cash))
        engine = PortfolioAccountingEngine(
            event_bus=bus,
            portfolio=portfolio,
            price_book=MarketPriceBook(),
            fill_guard=FillDeduplicationGuard(),
            now=clock.now,
        )
        return bus, clock, portfolio, engine

    def result(self, *, status, fills, filled_quantity, client_order_id="BOT-1"):
        return ExecutionResult(
            request_id="req-1",
            client_order_id=client_order_id,
            broker_order_id="mock-1",
            status=status,
            requested_quantity=Decimal("2"),
            filled_quantity=Decimal(str(filled_quantity)),
            average_fill_price=None if not fills else Decimal("50"),
            updated_at=self.now,
            fills=tuple(fills),
        )

    def test_buy_fill_updates_cash_and_position(self):
        _, _, portfolio, engine = self.engine()
        fill = FillRecord(Decimal("1"), Decimal("50"), self.now)
        snap = engine.process_execution_update(
            result=self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[fill], filled_quantity="1"),
            side=TradeSide.BUY,
            symbol="AAPL",
        )
        self.assertEqual(portfolio.cash, Decimal("950"))
        self.assertEqual(portfolio.positions["AAPL"].quantity, Decimal("1"))
        self.assertEqual(snap.equity, Decimal("1000"))

    def test_average_price_weighted(self):
        _, _, portfolio, engine = self.engine()
        fill1 = FillRecord(Decimal("1"), Decimal("50"), self.now)
        fill2 = FillRecord(Decimal("1"), Decimal("60"), self.now + timedelta(seconds=1))
        engine.process_execution_update(
            result=self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[fill1], filled_quantity="1"),
            side=TradeSide.BUY,
            symbol="AAPL",
        )
        engine.process_execution_update(
            result=self.result(status=ExecutionStatus.FILLED, fills=[fill1, fill2], filled_quantity="2"),
            side=TradeSide.BUY,
            symbol="AAPL",
        )
        self.assertEqual(portfolio.positions["AAPL"].average_price, Decimal("55"))

    def test_sell_realized_pnl(self):
        _, _, portfolio, engine = self.engine()
        buy = FillRecord(Decimal("2"), Decimal("50"), self.now)
        engine.process_execution_update(
            result=self.result(status=ExecutionStatus.FILLED, fills=[buy], filled_quantity="2"),
            side=TradeSide.BUY,
            symbol="AAPL",
        )
        sell = FillRecord(Decimal("1"), Decimal("60"), self.now + timedelta(seconds=1))
        sell_result = ExecutionResult(
            request_id="req-2",
            client_order_id="BOT-2",
            broker_order_id="mock-2",
            status=ExecutionStatus.PARTIALLY_FILLED,
            requested_quantity=Decimal("2"),
            filled_quantity=Decimal("1"),
            average_fill_price=Decimal("60"),
            updated_at=self.now + timedelta(seconds=1),
            fills=(sell,),
        )
        snap = engine.process_execution_update(
            result=sell_result,
            side=TradeSide.SELL,
            symbol="AAPL",
        )
        self.assertEqual(portfolio.realized_pnl, Decimal("10"))
        self.assertEqual(snap.cash, Decimal("960"))
        self.assertEqual(portfolio.positions["AAPL"].quantity, Decimal("1"))

    def test_unrealized_pnl(self):
        _, _, _, engine = self.engine()
        fill = FillRecord(Decimal("1"), Decimal("50"), self.now)
        engine.process_execution_update(
            result=self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[fill], filled_quantity="1"),
            side=TradeSide.BUY,
            symbol="AAPL",
        )
        engine.price_book.update("AAPL", Decimal("55"))
        snap = engine.snapshot()
        self.assertEqual(snap.unrealized_pnl, Decimal("5"))
        self.assertEqual(snap.equity, Decimal("1005"))

    def test_partial_then_full_processes_only_new_fill(self):
        _, _, portfolio, engine = self.engine()
        fill1 = FillRecord(Decimal("1"), Decimal("50"), self.now)
        fill2 = FillRecord(Decimal("1"), Decimal("50"), self.now + timedelta(seconds=1))
        partial = self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[fill1], filled_quantity="1")
        full = self.result(status=ExecutionStatus.FILLED, fills=[fill1, fill2], filled_quantity="2")
        engine.process_execution_update(result=partial, side=TradeSide.BUY, symbol="AAPL")
        engine.process_execution_update(result=full, side=TradeSide.BUY, symbol="AAPL")
        self.assertEqual(portfolio.positions["AAPL"].quantity, Decimal("2"))
        self.assertEqual(engine.stats.fills_processed, 2)

    def test_rejected_update_ignored(self):
        _, _, portfolio, engine = self.engine()
        rejected = ExecutionResult(
            request_id="req-r",
            client_order_id="BOT-R",
            broker_order_id=None,
            status=ExecutionStatus.REJECTED,
            requested_quantity=Decimal("1"),
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            updated_at=self.now,
            fills=(),
            rejection_reason="rejected",
        )
        self.assertIsNone(engine.process_execution_update(
            result=rejected,
            side=TradeSide.BUY,
            symbol="AAPL",
        ))
        self.assertEqual(portfolio.cash, Decimal("1000"))

    def test_insufficient_cash_rejected(self):
        _, _, _, engine = self.engine(cash="10")
        fill = FillRecord(Decimal("1"), Decimal("50"), self.now)
        with self.assertRaises(ValueError):
            engine.process_execution_update(
                result=self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[fill], filled_quantity="1"),
                side=TradeSide.BUY,
                symbol="AAPL",
            )

    def test_insufficient_position_rejected(self):
        _, _, _, engine = self.engine()
        fill = FillRecord(Decimal("1"), Decimal("50"), self.now)
        with self.assertRaises(ValueError):
            engine.process_execution_update(
                result=self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[fill], filled_quantity="1"),
                side=TradeSide.SELL,
                symbol="AAPL",
            )

    def test_event_bus_publishes_snapshot(self):
        bus, _, _, engine = self.engine()
        snapshots = []
        bus.subscribe("portfolio.snapshot", lambda event: snapshots.append(event.payload["snapshot"]))
        engine.start()
        fill = FillRecord(Decimal("1"), Decimal("50"), self.now)
        result = self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[fill], filled_quantity="1")
        bus.publish(Event(
            "execution.update",
            {"result":result, "side":"BUY", "symbol":"AAPL"},
            self.now,
        ))
        engine.stop()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(engine.stats.snapshots_published, 1)

    def test_buying_power(self):
        _, _, _, engine = self.engine()
        engine.buying_power_multiplier = Decimal("2")
        self.assertEqual(engine.snapshot().buying_power, Decimal("2000"))

    def test_price_book_validation(self):
        book = MarketPriceBook()
        book.update("AAPL", Decimal("50"))
        self.assertEqual(book.get("AAPL"), Decimal("50"))
        with self.assertRaises(ValueError):
            book.update("aapl", Decimal("50"))

    def test_fill_guard(self):
        guard = FillDeduplicationGuard()
        self.assertTrue(guard.register("fill-1"))
        self.assertFalse(guard.register("fill-1"))

    def test_position_closed_resets_average_price(self):
        _, _, portfolio, engine = self.engine()
        buy = FillRecord(Decimal("1"), Decimal("50"), self.now)
        engine.process_execution_update(
            result=self.result(status=ExecutionStatus.PARTIALLY_FILLED, fills=[buy], filled_quantity="1"),
            side=TradeSide.BUY,
            symbol="AAPL",
        )
        sell = FillRecord(Decimal("1"), Decimal("60"), self.now + timedelta(seconds=1))
        sell_result = ExecutionResult(
            request_id="req-2",
            client_order_id="BOT-2",
            broker_order_id="mock-2",
            status=ExecutionStatus.FILLED,
            requested_quantity=Decimal("1"),
            filled_quantity=Decimal("1"),
            average_fill_price=Decimal("60"),
            updated_at=self.now + timedelta(seconds=1),
            fills=(sell,),
        )
        engine.process_execution_update(result=sell_result, side=TradeSide.SELL, symbol="AAPL")
        self.assertEqual(portfolio.positions["AAPL"].quantity, Decimal("0"))
        self.assertEqual(portfolio.positions["AAPL"].average_price, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
