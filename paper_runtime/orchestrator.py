from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from execution_engine import (
    ExecutionStatus,
    MockPaperTransport,
    OrderIntentEngine,
    PaperExecutionAdapter,
)
from portfolio_engine import PortfolioAccountingEngine
from risk_engine import RiskDecisionStatus, RuntimeRiskManager
from strategy_engine import MarketSnapshot, SignalEngine

from .models import RuntimeCycleResult, RuntimeLifecycleState
from .recovery import PaperRuntimeRecoveryManager


@dataclass
class EndToEndRuntimeStats:
    cycles_started: int = 0
    cycles_completed: int = 0
    signals_generated: int = 0
    intents_created: int = 0
    risk_approved: int = 0
    risk_rejected: int = 0
    risk_halted: int = 0
    execution_accepted: int = 0
    fills_completed: int = 0
    recovery_snapshots: int = 0
    failures: int = 0


class EndToEndPaperRuntime:
    """Synchronous offline runtime joining all broker-independent foundations."""

    def __init__(
        self,
        *,
        signal_engine: SignalEngine,
        intent_engine: OrderIntentEngine,
        risk_manager: RuntimeRiskManager,
        execution_adapter: PaperExecutionAdapter,
        mock_transport: MockPaperTransport,
        portfolio_engine: PortfolioAccountingEngine,
        recovery_manager: PaperRuntimeRecoveryManager,
        now: Callable[[], datetime],
    ) -> None:
        self.signal_engine = signal_engine
        self.intent_engine = intent_engine
        self.risk_manager = risk_manager
        self.execution_adapter = execution_adapter
        self.mock_transport = mock_transport
        self.portfolio_engine = portfolio_engine
        self.recovery_manager = recovery_manager
        self.now = now
        self.state = RuntimeLifecycleState.CREATED
        self.stats = EndToEndRuntimeStats()
        self.heartbeat_count = 0
        self.last_error: str | None = None

    def start(self) -> None:
        if self.state not in {RuntimeLifecycleState.CREATED, RuntimeLifecycleState.STOPPED}:
            raise RuntimeError("runtime cannot start from current state")
        self.state = RuntimeLifecycleState.READY
        self.last_error = None

    def stop(self) -> None:
        if self.state == RuntimeLifecycleState.FAILED:
            return
        self.state = RuntimeLifecycleState.STOPPED
        self._save_recovery()

    def heartbeat(self) -> None:
        if self.state not in {RuntimeLifecycleState.READY, RuntimeLifecycleState.RUNNING}:
            raise RuntimeError("heartbeat requires active runtime")
        self.heartbeat_count += 1

    def run_cycle(self, snapshot: MarketSnapshot) -> RuntimeCycleResult:
        if self.state != RuntimeLifecycleState.READY:
            raise RuntimeError("runtime must be READY")
        self.state = RuntimeLifecycleState.RUNNING
        self.stats.cycles_started += 1
        cycle_id = self.stats.cycles_started

        try:
            signals = self.signal_engine.evaluate(snapshot)
            self.stats.signals_generated += len(signals)
            if not signals:
                result = self._result(
                    cycle_id, snapshot, 0, False, None, None, None, False, "no_signal"
                )
                self.state = RuntimeLifecycleState.READY
                self._save_recovery()
                return result

            signal = signals[0]
            intent = self.intent_engine.process(signal)
            if intent is None:
                result = self._result(
                    cycle_id, snapshot, len(signals), False, None, None, None, False, "intent_rejected"
                )
                self.state = RuntimeLifecycleState.READY
                self._save_recovery()
                return result
            self.stats.intents_created += 1

            decision = self.risk_manager.evaluate(intent)
            if decision.status == RiskDecisionStatus.REJECTED:
                self.stats.risk_rejected += 1
                result = self._result(
                    cycle_id, snapshot, len(signals), True, decision.status.value,
                    None, None, False, decision.reason
                )
                self.state = RuntimeLifecycleState.READY
                self._save_recovery()
                return result
            if decision.status == RiskDecisionStatus.HALTED:
                self.stats.risk_halted += 1
                result = self._result(
                    cycle_id, snapshot, len(signals), True, decision.status.value,
                    None, None, False, decision.reason
                )
                self.state = RuntimeLifecycleState.READY
                self._save_recovery()
                return result
            self.stats.risk_approved += 1

            request, accepted = self.execution_adapter.submit(intent, self.now())
            if accepted.status != ExecutionStatus.ACCEPTED:
                result = self._result(
                    cycle_id, snapshot, len(signals), True, decision.status.value,
                    accepted.status.value, None, False, accepted.rejection_reason or "execution_rejected"
                )
                self.state = RuntimeLifecycleState.READY
                self._save_recovery()
                return result
            self.stats.execution_accepted += 1

            filled = self.mock_transport.simulate_full_fill(request.client_order_id, self.now())
            portfolio_snapshot = self.portfolio_engine.process_execution_update(
                result=filled,
                side=intent.side.value,
                symbol=intent.symbol,
            )
            self.risk_manager.update_portfolio(portfolio_snapshot)
            self.stats.fills_completed += 1
            self.stats.cycles_completed += 1

            result = RuntimeCycleResult(
                cycle_id=cycle_id,
                symbol=snapshot.symbol,
                signal_count=len(signals),
                intent_created=True,
                risk_status=decision.status.value,
                execution_status=accepted.status.value,
                fill_status=filled.status.value,
                portfolio_equity=portfolio_snapshot.equity,
                portfolio_cash=portfolio_snapshot.cash,
                completed=True,
                reason="completed",
            )
            self.state = RuntimeLifecycleState.READY
            self._save_recovery()
            return result
        except Exception as exc:
            self.stats.failures += 1
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.state = RuntimeLifecycleState.FAILED
            self._save_recovery()
            raise

    def _result(
        self,
        cycle_id: int,
        snapshot: MarketSnapshot,
        signal_count: int,
        intent_created: bool,
        risk_status: str | None,
        execution_status: str | None,
        fill_status: str | None,
        completed: bool,
        reason: str,
    ) -> RuntimeCycleResult:
        portfolio = self.portfolio_engine.snapshot()
        return RuntimeCycleResult(
            cycle_id=cycle_id,
            symbol=snapshot.symbol,
            signal_count=signal_count,
            intent_created=intent_created,
            risk_status=risk_status,
            execution_status=execution_status,
            fill_status=fill_status,
            portfolio_equity=portfolio.equity,
            portfolio_cash=portfolio.cash,
            completed=completed,
            reason=reason,
        )

    def _save_recovery(self) -> None:
        portfolio = self.portfolio_engine.snapshot()
        risk = self.risk_manager.snapshot()
        self.recovery_manager.save(
            state=self.state.value,
            captured_at=self.now(),
            heartbeat_count=self.heartbeat_count,
            cycle_count=self.stats.cycles_started,
            portfolio=portfolio,
            risk=risk,
        )
        self.stats.recovery_snapshots += 1
