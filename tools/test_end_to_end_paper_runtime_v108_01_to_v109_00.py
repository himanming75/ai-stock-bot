from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime_engine import EventBus, JsonRecoveryStore, ManualClock
from strategy_engine import (
    ConfidenceFilter,
    CooldownFilter,
    DuplicateSignalGuard,
    MarketSnapshot,
    MovingAverageCrossStrategy,
    RiskPreFilter,
    SignalEngine,
)
from execution_engine import (
    AlpacaPaperPayloadBuilder,
    ClientOrderIdGenerator,
    DuplicateIntentGuard,
    ExecutionIdempotencyGuard,
    IntentExpiryPolicy,
    MockPaperTransport,
    OrderIntentEngine,
    OrderIntentFactory,
    PaperExecutionAdapter,
    PositionSizer,
    PositionSizingConfig,
)
from portfolio_engine import FillDeduplicationGuard, MarketPriceBook, Portfolio, PortfolioAccountingEngine
from risk_engine import RiskLimits, RuntimeRiskManager, RuntimeRiskState
from paper_runtime import EndToEndPaperRuntime, PaperRuntimeRecoveryManager, RuntimeLifecycleState


class EndToEndPaperRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
        self.clock = ManualClock(self.now)
        self.bus = EventBus()
        self.market_snapshot = MarketSnapshot(
            symbol="AAPL",
            timestamp=self.now,
            last_price=Decimal("50"),
            bid_price=Decimal("49.99"),
            ask_price=Decimal("50.01"),
            recent_closes=(Decimal("40"), Decimal("40"), Decimal("60"), Decimal("60")),
            position_quantity=Decimal("0"),
            cash_available=Decimal("1000"),
        )

    def tearDown(self):
        self.temp.cleanup()

    def runtime(self, *, max_total="500", allow_buys=True):
        portfolio = Portfolio(starting_cash=Decimal("1000"))
        price_book = MarketPriceBook()
        portfolio_engine = PortfolioAccountingEngine(
            event_bus=self.bus,
            portfolio=portfolio,
            price_book=price_book,
            fill_guard=FillDeduplicationGuard(),
            now=self.clock.now,
        )
        signal_engine = SignalEngine(
            event_bus=self.bus,
            strategies=[MovingAverageCrossStrategy(short_window=2, long_window=4)],
            confidence_filter=ConfidenceFilter(Decimal("0.10")),
            cooldown_filter=CooldownFilter(cooldown_seconds=0),
            duplicate_guard=DuplicateSignalGuard(ttl_seconds=1),
            risk_filter=RiskPreFilter(max_quantity=Decimal("1"), max_notional=Decimal("100")),
        )
        intent_engine = OrderIntentEngine(
            event_bus=self.bus,
            intent_factory=OrderIntentFactory(
                position_sizer=PositionSizer(PositionSizingConfig(
                    max_quantity=Decimal("1"),
                    max_order_notional=Decimal("100"),
                    cash_fraction=Decimal("0.10"),
                )),
                ttl_seconds=30,
            ),
            duplicate_guard=DuplicateIntentGuard(ttl_seconds=1),
            expiry_policy=IntentExpiryPolicy(),
            snapshot_provider=lambda symbol: self.market_snapshot,
            now=self.clock.now,
        )
        transport = MockPaperTransport(default_fill_price=Decimal("50"))
        adapter = PaperExecutionAdapter(
            transport=transport,
            payload_builder=AlpacaPaperPayloadBuilder(),
            client_order_id_generator=ClientOrderIdGenerator(),
            idempotency_guard=ExecutionIdempotencyGuard(),
        )
        risk = RuntimeRiskManager(
            event_bus=self.bus,
            limits=RiskLimits(
                max_daily_loss=Decimal("50"),
                max_drawdown=Decimal("100"),
                max_symbol_exposure=Decimal("250"),
                max_total_exposure=Decimal(max_total),
                max_open_positions=3,
                max_consecutive_losses=3,
                allow_new_buys=allow_buys,
            ),
            state=RuntimeRiskState(current_equity=Decimal("1000"), peak_equity=Decimal("1000")),
            now=self.clock.now,
        )
        recovery = PaperRuntimeRecoveryManager(
            JsonRecoveryStore(Path(self.temp.name) / "recovery.json")
        )
        return EndToEndPaperRuntime(
            signal_engine=signal_engine,
            intent_engine=intent_engine,
            risk_manager=risk,
            execution_adapter=adapter,
            mock_transport=transport,
            portfolio_engine=portfolio_engine,
            recovery_manager=recovery,
            now=self.clock.now,
        ), portfolio, recovery

    def test_lifecycle(self):
        runtime, _, _ = self.runtime()
        self.assertEqual(runtime.state, RuntimeLifecycleState.CREATED)
        runtime.start()
        self.assertEqual(runtime.state, RuntimeLifecycleState.READY)
        runtime.stop()
        self.assertEqual(runtime.state, RuntimeLifecycleState.STOPPED)

    def test_successful_cycle(self):
        runtime, portfolio, _ = self.runtime()
        runtime.start()
        result = runtime.run_cycle(self.market_snapshot)
        self.assertTrue(result.completed)
        self.assertEqual(result.risk_status, "APPROVED")
        self.assertEqual(result.execution_status, "ACCEPTED")
        self.assertEqual(result.fill_status, "FILLED")
        self.assertEqual(portfolio.positions["AAPL"].quantity, Decimal("1"))

    def test_cash_reduced_after_buy(self):
        runtime, portfolio, _ = self.runtime()
        runtime.start()
        runtime.run_cycle(self.market_snapshot)
        self.assertEqual(portfolio.cash, Decimal("950"))

    def test_equity_preserved_at_equal_fill_price(self):
        runtime, _, _ = self.runtime()
        runtime.start()
        result = runtime.run_cycle(self.market_snapshot)
        self.assertEqual(result.portfolio_equity, Decimal("1000"))

    def test_risk_rejection_prevents_execution(self):
        runtime, portfolio, _ = self.runtime(max_total="10")
        runtime.start()
        result = runtime.run_cycle(self.market_snapshot)
        self.assertFalse(result.completed)
        self.assertEqual(result.risk_status, "REJECTED")
        self.assertEqual(portfolio.cash, Decimal("1000"))
        self.assertEqual(runtime.stats.execution_accepted, 0)

    def test_new_buy_disabled_rejection(self):
        runtime, _, _ = self.runtime(allow_buys=False)
        runtime.start()
        result = runtime.run_cycle(self.market_snapshot)
        self.assertEqual(result.reason, "new_buys_disabled")

    def test_heartbeat(self):
        runtime, _, _ = self.runtime()
        runtime.start()
        runtime.heartbeat()
        runtime.heartbeat()
        self.assertEqual(runtime.heartbeat_count, 2)

    def test_recovery_saved_after_cycle(self):
        runtime, _, recovery = self.runtime()
        runtime.start()
        runtime.run_cycle(self.market_snapshot)
        metadata = recovery.load_metadata()
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["cycle_count"], 1)
        self.assertEqual(metadata["state"], "READY")

    def test_stats_success(self):
        runtime, _, _ = self.runtime()
        runtime.start()
        runtime.run_cycle(self.market_snapshot)
        self.assertEqual(runtime.stats.cycles_started, 1)
        self.assertEqual(runtime.stats.cycles_completed, 1)
        self.assertEqual(runtime.stats.signals_generated, 1)
        self.assertEqual(runtime.stats.fills_completed, 1)

    def test_requires_ready_state(self):
        runtime, _, _ = self.runtime()
        with self.assertRaises(RuntimeError):
            runtime.run_cycle(self.market_snapshot)

    def test_duplicate_signal_results_no_signal(self):
        runtime, _, _ = self.runtime()
        runtime.start()
        first = runtime.run_cycle(self.market_snapshot)
        self.assertTrue(first.completed)
        runtime.state = RuntimeLifecycleState.READY
        second = runtime.run_cycle(self.market_snapshot)
        self.assertFalse(second.completed)
        self.assertEqual(second.reason, "no_signal")

    def test_stop_saves_recovery(self):
        runtime, _, recovery = self.runtime()
        runtime.start()
        runtime.stop()
        metadata = recovery.load_metadata()
        self.assertEqual(metadata["state"], "STOPPED")


if __name__ == "__main__":
    unittest.main()
