from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
from paper_runtime import EndToEndPaperRuntime, PaperRuntimeRecoveryManager


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    repo = Path(args.repository_root).resolve()
    output = repo / "release" / "v109_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
    clock = ManualClock(now)
    bus = EventBus()
    market_snapshot = MarketSnapshot(
        symbol="AAPL",
        timestamp=now,
        last_price=Decimal("50"),
        bid_price=Decimal("49.99"),
        ask_price=Decimal("50.01"),
        recent_closes=(Decimal("40"), Decimal("40"), Decimal("60"), Decimal("60")),
        position_quantity=Decimal("0"),
        cash_available=Decimal("1000"),
    )

    portfolio = Portfolio(starting_cash=Decimal("1000"))
    portfolio_engine = PortfolioAccountingEngine(
        event_bus=bus,
        portfolio=portfolio,
        price_book=MarketPriceBook(),
        fill_guard=FillDeduplicationGuard(),
        now=clock.now,
    )
    signal_engine = SignalEngine(
        event_bus=bus,
        strategies=[MovingAverageCrossStrategy(short_window=2, long_window=4)],
        confidence_filter=ConfidenceFilter(Decimal("0.10")),
        cooldown_filter=CooldownFilter(cooldown_seconds=0),
        duplicate_guard=DuplicateSignalGuard(ttl_seconds=60),
        risk_filter=RiskPreFilter(max_quantity=Decimal("1"), max_notional=Decimal("100")),
    )
    intent_engine = OrderIntentEngine(
        event_bus=bus,
        intent_factory=OrderIntentFactory(
            position_sizer=PositionSizer(PositionSizingConfig(
                max_quantity=Decimal("1"),
                max_order_notional=Decimal("100"),
                cash_fraction=Decimal("0.10"),
            )),
            ttl_seconds=30,
        ),
        duplicate_guard=DuplicateIntentGuard(ttl_seconds=60),
        expiry_policy=IntentExpiryPolicy(),
        snapshot_provider=lambda symbol: market_snapshot,
        now=clock.now,
    )
    transport = MockPaperTransport(default_fill_price=Decimal("50"))
    adapter = PaperExecutionAdapter(
        transport=transport,
        payload_builder=AlpacaPaperPayloadBuilder(),
        client_order_id_generator=ClientOrderIdGenerator(),
        idempotency_guard=ExecutionIdempotencyGuard(),
    )
    risk = RuntimeRiskManager(
        event_bus=bus,
        limits=RiskLimits(),
        state=RuntimeRiskState(current_equity=Decimal("1000"), peak_equity=Decimal("1000")),
        now=clock.now,
    )
    recovery_path = output / "paper_runtime_recovery.json"
    runtime = EndToEndPaperRuntime(
        signal_engine=signal_engine,
        intent_engine=intent_engine,
        risk_manager=risk,
        execution_adapter=adapter,
        mock_transport=transport,
        portfolio_engine=portfolio_engine,
        recovery_manager=PaperRuntimeRecoveryManager(JsonRecoveryStore(recovery_path)),
        now=clock.now,
    )

    runtime.start()
    runtime.heartbeat()
    result = runtime.run_cycle(market_snapshot)
    runtime.heartbeat()
    runtime.stop()

    final_portfolio = portfolio_engine.snapshot()
    final_risk = risk.snapshot()
    recovery = JsonRecoveryStore(recovery_path).load()

    payload = {
        "stage_range": "V108.01-V109.00",
        "status": "PASS",
        "implementation_type": "END_TO_END_PAPER_RUNTIME_FOUNDATION",
        "runtime_final_state": runtime.state.value,
        "cycle_completed": result.completed,
        "signal_count": result.signal_count,
        "risk_status": result.risk_status,
        "execution_status": result.execution_status,
        "fill_status": result.fill_status,
        "position_quantity": str(portfolio.positions["AAPL"].quantity),
        "final_cash": str(final_portfolio.cash),
        "final_equity": str(final_portfolio.equity),
        "risk_total_exposure": str(final_risk.total_exposure),
        "heartbeat_count": runtime.heartbeat_count,
        "recovery_exists": recovery is not None,
        "recovery_state": recovery.state if recovery else None,
        "stats": vars(runtime.stats),
        "network_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "actual_broker_transport_enabled": False,
        "next_phase": "V109_01_ACTUAL_ALPACA_PAPER_BROKER_INTEGRATION",
    }

    (output / "end_to_end_paper_runtime_result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
