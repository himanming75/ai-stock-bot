from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from runtime_engine import Event, EventBus
from execution_engine import ExecutionResult, ExecutionStatus

from .dedup import FillDeduplicationGuard
from .models import (
    Portfolio,
    PortfolioSnapshot,
    PositionSnapshot,
    TradeSide,
)
from .valuation import MarketPriceBook


@dataclass
class PortfolioAccountingStats:
    execution_updates_received: int = 0
    fills_processed: int = 0
    duplicate_fills_rejected: int = 0
    rejected_updates_ignored: int = 0
    partial_fills_processed: int = 0
    full_fills_processed: int = 0
    snapshots_published: int = 0


class PortfolioAccountingEngine:
    """Apply execution fills to cash, positions, P/L, and portfolio valuation."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        portfolio: Portfolio,
        price_book: MarketPriceBook,
        fill_guard: FillDeduplicationGuard,
        now: Callable[[], datetime],
        buying_power_multiplier: Decimal = Decimal("1"),
    ) -> None:
        if buying_power_multiplier <= 0:
            raise ValueError("buying_power_multiplier must be positive")
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.price_book = price_book
        self.fill_guard = fill_guard
        self.now = now
        self.buying_power_multiplier = buying_power_multiplier
        self.stats = PortfolioAccountingStats()
        self._unsubscribe = None
        self._processed_fill_count_by_order: dict[str, int] = {}

    def start(self) -> None:
        if self._unsubscribe is not None:
            raise RuntimeError("engine already started")
        self._unsubscribe = self.event_bus.subscribe("execution.update", self._handle_execution_update)

    def stop(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _handle_execution_update(self, event: Event) -> None:
        result = event.payload.get("result")
        side = event.payload.get("side")
        symbol = event.payload.get("symbol")
        if not isinstance(result, ExecutionResult):
            raise TypeError("execution.update requires ExecutionResult")
        if side not in {"BUY", "SELL"}:
            raise ValueError("execution.update requires BUY or SELL side")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("execution.update requires symbol")
        self.process_execution_update(
            result=result,
            side=TradeSide(side),
            symbol=symbol.upper(),
        )

    def process_execution_update(
        self,
        *,
        result: ExecutionResult,
        side: TradeSide,
        symbol: str,
    ) -> PortfolioSnapshot | None:
        result.validate()
        self.stats.execution_updates_received += 1

        if result.status == ExecutionStatus.REJECTED:
            self.stats.rejected_updates_ignored += 1
            return None

        processed_count = self._processed_fill_count_by_order.get(result.client_order_id, 0)
        new_fills = result.fills[processed_count:]
        if not new_fills:
            return self.snapshot()

        position = self.portfolio.get_position(symbol)

        for index, fill in enumerate(new_fills, start=processed_count):
            fill_id = f"{result.client_order_id}:{index}:{fill.quantity}:{fill.price}:{fill.filled_at.isoformat()}"
            if not self.fill_guard.register(fill_id):
                self.stats.duplicate_fills_rejected += 1
                continue

            notional = fill.quantity * fill.price
            if side == TradeSide.BUY:
                if notional > self.portfolio.cash:
                    raise ValueError("insufficient cash for fill")
                self.portfolio.cash -= notional
                position.apply_buy(fill.quantity, fill.price)
            else:
                realized = position.apply_sell(fill.quantity, fill.price)
                self.portfolio.cash += notional
                self.portfolio.realized_pnl += realized

            self.price_book.update(symbol, fill.price)
            self.stats.fills_processed += 1

        self._processed_fill_count_by_order[result.client_order_id] = len(result.fills)

        if result.status == ExecutionStatus.PARTIALLY_FILLED:
            self.stats.partial_fills_processed += 1
        if result.status == ExecutionStatus.FILLED:
            self.stats.full_fills_processed += 1

        snapshot = self.snapshot()
        self.event_bus.publish(Event(
            topic="portfolio.snapshot",
            payload={"snapshot": snapshot},
            created_at=self.now(),
        ))
        self.stats.snapshots_published += 1
        return snapshot

    def snapshot(self) -> PortfolioSnapshot:
        position_snapshots: list[PositionSnapshot] = []
        total_market_value = Decimal("0")
        total_unrealized = Decimal("0")

        for symbol, position in sorted(self.portfolio.positions.items()):
            if position.quantity == 0:
                continue
            market_price = self.price_book.get(symbol, fallback=position.average_price)
            market_value = position.quantity * market_price
            unrealized = position.quantity * (market_price - position.average_price)
            total_market_value += market_value
            total_unrealized += unrealized
            position_snapshots.append(PositionSnapshot(
                symbol=symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                market_price=market_price,
                market_value=market_value,
                unrealized_pnl=unrealized,
                realized_pnl=position.realized_pnl,
            ))

        equity = self.portfolio.cash + total_market_value
        buying_power = self.portfolio.cash * self.buying_power_multiplier

        return PortfolioSnapshot(
            captured_at=self.now(),
            cash=self.portfolio.cash,
            equity=equity,
            market_value=total_market_value,
            realized_pnl=self.portfolio.realized_pnl,
            unrealized_pnl=total_unrealized,
            buying_power=buying_power,
            positions=tuple(position_snapshots),
            metadata={
                "starting_cash": str(self.portfolio.starting_cash),
                "position_count": len(position_snapshots),
            },
        )
