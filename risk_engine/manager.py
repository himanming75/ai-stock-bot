from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from runtime_engine import Event, EventBus
from execution_engine import OrderIntent, OrderSide
from portfolio_engine import PortfolioSnapshot

from .models import RiskDecision, RiskDecisionStatus, RiskLimits, RiskSnapshot
from .state import RuntimeRiskState


@dataclass
class RuntimeRiskStats:
    intents_received: int = 0
    approved: int = 0
    rejected: int = 0
    halted: int = 0
    portfolio_updates_received: int = 0
    snapshots_published: int = 0


class RuntimeRiskManager:
    """Final runtime gate for broker-independent order intents."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        limits: RiskLimits,
        state: RuntimeRiskState,
        now: Callable[[], datetime],
    ) -> None:
        limits.validate()
        self.event_bus = event_bus
        self.limits = limits
        self.state = state
        self.now = now
        self.stats = RuntimeRiskStats()
        self.last_decision: RiskDecision | None = None
        self._unsub_intent = None
        self._unsub_portfolio = None

    def start(self) -> None:
        if self._unsub_intent is not None or self._unsub_portfolio is not None:
            raise RuntimeError("risk manager already started")
        self._unsub_intent = self.event_bus.subscribe("order.intent", self._handle_intent)
        self._unsub_portfolio = self.event_bus.subscribe("portfolio.snapshot", self._handle_portfolio)

    def stop(self) -> None:
        if self._unsub_intent is not None:
            self._unsub_intent()
            self._unsub_intent = None
        if self._unsub_portfolio is not None:
            self._unsub_portfolio()
            self._unsub_portfolio = None

    def _handle_intent(self, event: Event) -> None:
        intent = event.payload.get("intent")
        if not isinstance(intent, OrderIntent):
            raise TypeError("order.intent event requires OrderIntent")
        self.evaluate(intent)

    def _handle_portfolio(self, event: Event) -> None:
        snapshot = event.payload.get("snapshot")
        if not isinstance(snapshot, PortfolioSnapshot):
            raise TypeError("portfolio.snapshot event requires PortfolioSnapshot")
        self.update_portfolio(snapshot)

    def update_portfolio(self, snapshot: PortfolioSnapshot) -> RiskSnapshot:
        self.stats.portfolio_updates_received += 1
        self.state.current_equity = snapshot.equity
        self.state.peak_equity = max(self.state.peak_equity, snapshot.equity)
        self.state.daily_realized_pnl = snapshot.realized_pnl
        self.state.total_exposure = snapshot.market_value
        self.state.open_position_count = len(snapshot.positions)

        if snapshot.realized_pnl < 0:
            self.state.consecutive_losses += 1
        elif snapshot.realized_pnl > 0:
            self.state.consecutive_losses = 0

        if -snapshot.realized_pnl >= self.limits.max_daily_loss:
            self.state.new_buys_allowed = False
        if self.state.drawdown >= self.limits.max_drawdown:
            self.state.engage_emergency_stop()
        if self.state.consecutive_losses >= self.limits.max_consecutive_losses:
            self.state.new_buys_allowed = False

        risk_snapshot = self.snapshot()
        self.event_bus.publish(Event(
            topic="risk.snapshot",
            payload={"snapshot": risk_snapshot},
            created_at=self.now(),
        ))
        self.stats.snapshots_published += 1
        return risk_snapshot

    def evaluate(self, intent: OrderIntent) -> RiskDecision:
        self.stats.intents_received += 1
        now = self.now()

        if self.state.kill_switch_engaged:
            return self._record(RiskDecision(
                RiskDecisionStatus.HALTED,
                "kill_switch_engaged",
                now,
                intent.intent_id,
                intent.symbol,
            ))

        if self.state.emergency_stop_engaged:
            return self._record(RiskDecision(
                RiskDecisionStatus.HALTED,
                "emergency_stop_engaged",
                now,
                intent.intent_id,
                intent.symbol,
            ))

        if intent.side == OrderSide.BUY:
            if not self.limits.allow_new_buys or not self.state.new_buys_allowed:
                return self._reject(intent, "new_buys_disabled")

            if self.state.open_position_count >= self.limits.max_open_positions:
                return self._reject(intent, "max_open_positions")

            projected_total = self.state.total_exposure + intent.estimated_notional
            if projected_total > self.limits.max_total_exposure:
                return self._reject(intent, "max_total_exposure")

            if intent.estimated_notional > self.limits.max_symbol_exposure:
                return self._reject(intent, "max_symbol_exposure")

        decision = RiskDecision(
            RiskDecisionStatus.APPROVED,
            "approved",
            now,
            intent.intent_id,
            intent.symbol,
            metadata={
                "estimated_notional": str(intent.estimated_notional),
                "total_exposure_before": str(self.state.total_exposure),
            },
        )
        return self._record(decision)

    def _reject(self, intent: OrderIntent, reason: str) -> RiskDecision:
        return self._record(RiskDecision(
            RiskDecisionStatus.REJECTED,
            reason,
            self.now(),
            intent.intent_id,
            intent.symbol,
        ))

    def _record(self, decision: RiskDecision) -> RiskDecision:
        self.last_decision = decision
        if decision.status == RiskDecisionStatus.APPROVED:
            self.stats.approved += 1
            topic = "risk.approved"
        elif decision.status == RiskDecisionStatus.REJECTED:
            self.stats.rejected += 1
            topic = "risk.rejected"
        else:
            self.stats.halted += 1
            topic = "risk.halted"

        self.event_bus.publish(Event(
            topic=topic,
            payload={"decision": decision},
            created_at=decision.checked_at,
        ))
        return decision

    def snapshot(self) -> RiskSnapshot:
        return RiskSnapshot(
            captured_at=self.now(),
            kill_switch_engaged=self.state.kill_switch_engaged,
            emergency_stop_engaged=self.state.emergency_stop_engaged,
            new_buys_allowed=self.state.new_buys_allowed,
            daily_realized_pnl=self.state.daily_realized_pnl,
            current_equity=self.state.current_equity,
            peak_equity=self.state.peak_equity,
            drawdown=self.state.drawdown,
            total_exposure=self.state.total_exposure,
            open_position_count=self.state.open_position_count,
            consecutive_losses=self.state.consecutive_losses,
            last_decision=self.last_decision,
        )
