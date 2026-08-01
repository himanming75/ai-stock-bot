from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from runtime_engine import Event, EventBus, ManualClock
from execution_engine import OrderIntent, OrderSide, OrderType, TimeInForce
from portfolio_engine import PortfolioSnapshot, PositionSnapshot
from risk_engine import (
    RiskDecisionStatus,
    RiskLimits,
    RuntimeRiskManager,
    RuntimeRiskState,
)


class RuntimeRiskManagerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)

    def intent(self, side=OrderSide.BUY, notional="50", symbol="AAPL"):
        return OrderIntent(
            symbol=symbol,
            side=side,
            quantity=Decimal("1"),
            reference_price=Decimal("50"),
            estimated_notional=Decimal(notional),
            created_at=self.now,
            expires_at=self.now + timedelta(seconds=30),
            source_signal_id="sig-1",
            strategy_name="demo",
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )

    def snapshot(self, equity="1000", realized="0", market="100", positions=1):
        position_list = tuple(
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
            captured_at=self.now,
            cash=Decimal(equity) - Decimal(market),
            equity=Decimal(equity),
            market_value=Decimal(market),
            realized_pnl=Decimal(realized),
            unrealized_pnl=Decimal("0"),
            buying_power=Decimal("1000"),
            positions=position_list,
        )

    def manager(self, limits=None, state=None):
        bus = EventBus()
        clock = ManualClock(self.now)
        manager = RuntimeRiskManager(
            event_bus=bus,
            limits=limits or RiskLimits(),
            state=state or RuntimeRiskState(current_equity=Decimal("1000"), peak_equity=Decimal("1000")),
            now=clock.now,
        )
        return bus, clock, manager

    def test_approve_normal_buy(self):
        _, _, manager = self.manager()
        decision = manager.evaluate(self.intent())
        self.assertEqual(decision.status, RiskDecisionStatus.APPROVED)

    def test_kill_switch_halts(self):
        state = RuntimeRiskState()
        state.engage_kill_switch()
        _, _, manager = self.manager(state=state)
        self.assertEqual(manager.evaluate(self.intent()).status, RiskDecisionStatus.HALTED)

    def test_emergency_stop_halts(self):
        state = RuntimeRiskState(emergency_stop_engaged=True, new_buys_allowed=False)
        _, _, manager = self.manager(state=state)
        self.assertEqual(manager.evaluate(self.intent()).status, RiskDecisionStatus.HALTED)

    def test_new_buys_disabled(self):
        state = RuntimeRiskState(new_buys_allowed=False)
        _, _, manager = self.manager(state=state)
        self.assertEqual(manager.evaluate(self.intent()).reason, "new_buys_disabled")

    def test_max_open_positions(self):
        state = RuntimeRiskState(open_position_count=3)
        _, _, manager = self.manager(state=state)
        self.assertEqual(manager.evaluate(self.intent()).reason, "max_open_positions")

    def test_max_total_exposure(self):
        state = RuntimeRiskState(total_exposure=Decimal("480"))
        _, _, manager = self.manager(state=state)
        self.assertEqual(manager.evaluate(self.intent(notional="30")).reason, "max_total_exposure")

    def test_max_symbol_exposure(self):
        _, _, manager = self.manager()
        self.assertEqual(manager.evaluate(self.intent(notional="300")).reason, "max_symbol_exposure")

    def test_sell_allowed_when_new_buys_disabled(self):
        state = RuntimeRiskState(new_buys_allowed=False)
        _, _, manager = self.manager(state=state)
        self.assertEqual(manager.evaluate(self.intent(side=OrderSide.SELL)).status, RiskDecisionStatus.APPROVED)

    def test_daily_loss_disables_buys(self):
        _, _, manager = self.manager()
        manager.update_portfolio(self.snapshot(realized="-50"))
        self.assertFalse(manager.state.new_buys_allowed)

    def test_drawdown_engages_emergency_stop(self):
        state = RuntimeRiskState(current_equity=Decimal("1000"), peak_equity=Decimal("1000"))
        _, _, manager = self.manager(state=state)
        manager.update_portfolio(self.snapshot(equity="900", realized="-10"))
        self.assertTrue(manager.state.emergency_stop_engaged)

    def test_consecutive_losses_disable_buys(self):
        limits = RiskLimits(max_consecutive_losses=2)
        _, _, manager = self.manager(limits=limits)
        manager.update_portfolio(self.snapshot(realized="-1"))
        manager.update_portfolio(self.snapshot(realized="-2"))
        self.assertFalse(manager.state.new_buys_allowed)

    def test_profit_resets_consecutive_losses(self):
        state = RuntimeRiskState(consecutive_losses=2)
        _, _, manager = self.manager(state=state)
        manager.update_portfolio(self.snapshot(realized="5"))
        self.assertEqual(manager.state.consecutive_losses, 0)

    def test_event_bus_risk_flow(self):
        bus, _, manager = self.manager()
        approved = []
        bus.subscribe("risk.approved", lambda event: approved.append(event.payload["decision"]))
        manager.start()
        bus.publish(Event("order.intent", {"intent":self.intent()}, self.now))
        manager.stop()
        self.assertEqual(len(approved), 1)

    def test_portfolio_snapshot_publishes_risk_snapshot(self):
        bus, _, manager = self.manager()
        snapshots = []
        bus.subscribe("risk.snapshot", lambda event: snapshots.append(event.payload["snapshot"]))
        manager.start()
        bus.publish(Event("portfolio.snapshot", {"snapshot":self.snapshot()}, self.now))
        manager.stop()
        self.assertEqual(len(snapshots), 1)

    def test_state_reset_session(self):
        state = RuntimeRiskState(kill_switch_engaged=True, emergency_stop_engaged=True, new_buys_allowed=False, consecutive_losses=3)
        state.reset_session()
        self.assertFalse(state.kill_switch_engaged)
        self.assertFalse(state.emergency_stop_engaged)
        self.assertTrue(state.new_buys_allowed)
        self.assertEqual(state.consecutive_losses, 0)


if __name__ == "__main__":
    unittest.main()
