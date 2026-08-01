from __future__ import annotations

from typing import Any

from .config import AutonomousRuntimeConfig
from .models import (
    AutonomousCycleResult,
    AutonomousDecision,
    AutonomousRuntimeState,
)
from .policy import AutonomousDecisionPolicy


class AutonomousAlpacaPaperRuntime:
    """Safe autonomous Paper foundation with explicit single-order opt-in."""

    def __init__(
        self,
        *,
        config: AutonomousRuntimeConfig,
        market_reader: Any,
        signal_provider: Any,
        order_preview_builder: Any,
        single_order_submitter: Any | None = None,
    ) -> None:
        config.validate()
        self.config = config
        self.market_reader = market_reader
        self.signal_provider = signal_provider
        self.order_preview_builder = order_preview_builder
        self.single_order_submitter = single_order_submitter
        self.policy = AutonomousDecisionPolicy(config)
        self.state = AutonomousRuntimeState.CREATED
        self.read_requests_executed = 0
        self.write_requests_executed = 0
        self.actual_paper_orders_submitted = 0
        self.live_orders_submitted = 0
        self.cycle_count = 0

    def start(self) -> None:
        if self.state not in {
            AutonomousRuntimeState.CREATED,
            AutonomousRuntimeState.STOPPED,
        }:
            raise RuntimeError(f"cannot start from {self.state.value}")
        self.state = AutonomousRuntimeState.READY

    def run_cycle(self) -> AutonomousCycleResult:
        if self.state not in {
            AutonomousRuntimeState.READY,
            AutonomousRuntimeState.RUNNING,
            AutonomousRuntimeState.WAITING,
            AutonomousRuntimeState.BLOCKED,
        }:
            raise RuntimeError("autonomous runtime is not started")

        self.cycle_count += 1
        self.state = AutonomousRuntimeState.RUNNING

        market_open = bool(self.market_reader.is_market_open())
        estimated_price = float(self.market_reader.get_price(self.config.symbol))
        signal_action = str(self.signal_provider.get_signal(self.config.symbol))

        if self.config.read_network_enabled:
            self.read_requests_executed += 2

        decision = self.policy.decide(
            market_open=market_open,
            signal_action=signal_action,
            estimated_price=estimated_price,
        )

        if decision in {
            AutonomousDecision.WAIT_MARKET_CLOSED,
            AutonomousDecision.WAIT_NO_SIGNAL,
        }:
            self.state = AutonomousRuntimeState.WAITING
            return self._result(decision, estimated_price, "no order action")

        if decision == AutonomousDecision.BLOCKED_READ_DISABLED:
            self.state = AutonomousRuntimeState.BLOCKED
            return self._result(decision, estimated_price, "read network opt-in is disabled")

        preview = self.order_preview_builder.build(
            symbol=self.config.symbol,
            quantity=self.config.max_quantity,
            estimated_price=estimated_price,
        )

        if decision in {
            AutonomousDecision.PREVIEW_ORDER,
            AutonomousDecision.BLOCKED_WRITE_DISABLED,
        }:
            self.state = AutonomousRuntimeState.BLOCKED
            return self._result(
                decision,
                estimated_price,
                f"preview generated: {preview['client_order_id']}",
            )

        if self.single_order_submitter is None:
            raise RuntimeError("single_order_submitter is required for write opt-in")

        response = self.single_order_submitter.submit(preview)
        self.write_requests_executed += 1
        self.actual_paper_orders_submitted += 1
        self.state = AutonomousRuntimeState.WAITING
        return self._result(
            decision,
            estimated_price,
            f"paper order submitted: {response['client_order_id']}",
        )

    def stop(self) -> None:
        self.state = AutonomousRuntimeState.STOPPED

    def _result(
        self,
        decision: AutonomousDecision,
        price: float,
        detail: str,
    ) -> AutonomousCycleResult:
        return AutonomousCycleResult(
            status="PASS",
            decision=decision,
            runtime_state=self.state,
            symbol=self.config.symbol,
            quantity=self.config.max_quantity,
            estimated_notional=round(price * self.config.max_quantity, 4),
            read_requests_executed=self.read_requests_executed,
            write_requests_executed=self.write_requests_executed,
            actual_paper_orders_submitted=self.actual_paper_orders_submitted,
            live_orders_submitted=self.live_orders_submitted,
            detail=detail,
        )
