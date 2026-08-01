from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .calendar import TradingCalendarPolicy
from .models import (
    MarketSessionPhase,
    SchedulerAction,
    SchedulerDecision,
    SchedulerState,
)
from .store import AtomicSchedulerStateStore


@dataclass(frozen=True)
class SessionSchedulerConfig:
    cycle_interval_seconds: int = 60
    heartbeat_interval_seconds: int = 30
    closed_poll_seconds: int = 300
    pre_market_poll_seconds: int = 60

    def validate(self) -> None:
        if not 1 <= self.cycle_interval_seconds <= 3600:
            raise ValueError("cycle interval must be between 1 and 3600 seconds")
        if not 1 <= self.heartbeat_interval_seconds <= 3600:
            raise ValueError("heartbeat interval must be between 1 and 3600 seconds")
        if not 1 <= self.closed_poll_seconds <= 86400:
            raise ValueError("closed poll must be between 1 and 86400 seconds")
        if not 1 <= self.pre_market_poll_seconds <= 3600:
            raise ValueError("pre-market poll must be between 1 and 3600 seconds")


class AlpacaPaperSessionScheduler:
    def __init__(
        self,
        *,
        calendar: TradingCalendarPolicy,
        store: AtomicSchedulerStateStore,
        config: SessionSchedulerConfig,
        now: Callable[[], datetime],
    ) -> None:
        config.validate()
        self.calendar = calendar
        self.store = store
        self.config = config
        self.now = now
        self.state = store.load() or SchedulerState()
        self.network_requests_executed = 0
        self.write_requests_executed = 0
        self.actual_paper_orders_submitted = 0
        self.live_orders_submitted = 0

    def recover(self) -> SchedulerDecision:
        moment = self.now()
        phase = self.calendar.phase_at(moment)
        session_date = self.calendar.session_date(moment)
        self.state.restart_count += 1
        self.state.current_phase = phase
        self.state.session_date = session_date
        self.state.last_transition_at = moment

        if self.state.session_active and phase == MarketSessionPhase.REGULAR:
            action = SchedulerAction.RECOVER_SESSION
            reason = "active_session_recovered"
        elif self.state.session_active and phase != MarketSessionPhase.REGULAR:
            self.state.session_active = False
            self.state.session_closed = True
            action = SchedulerAction.CLOSE_SESSION
            reason = "stale_active_session_closed"
        else:
            action = SchedulerAction.WAIT
            reason = "no_active_session_to_recover"

        self.state.last_action = action
        self.store.save(self.state)
        return SchedulerDecision(
            decided_at=moment,
            phase=phase,
            action=action,
            reason=reason,
            session_date=session_date,
            next_wakeup_seconds=self._next_wakeup(phase),
        )

    def tick(self) -> SchedulerDecision:
        moment = self.now()
        phase = self.calendar.phase_at(moment)
        session_date = self.calendar.session_date(moment)

        if self.state.session_date != session_date:
            self.state.session_date = session_date
            self.state.session_active = False
            self.state.session_prepared = False
            self.state.session_closed = False
            self.state.cycle_count = 0

        action, reason = self._decide(phase)
        self.state.current_phase = phase
        self.state.last_action = action
        self.state.last_transition_at = moment

        if action == SchedulerAction.PREPARE:
            self.state.session_prepared = True
        elif action == SchedulerAction.START_SESSION:
            self.state.session_active = True
            self.state.session_closed = False
        elif action == SchedulerAction.RUN_CYCLE:
            self.state.cycle_count += 1
        elif action == SchedulerAction.CLOSE_SESSION:
            self.state.session_active = False
            self.state.session_closed = True

        self.state.heartbeat_count += 1
        self.store.save(self.state)

        return SchedulerDecision(
            decided_at=moment,
            phase=phase,
            action=action,
            reason=reason,
            session_date=session_date,
            next_wakeup_seconds=self._next_wakeup(phase),
        )

    def _decide(self, phase: MarketSessionPhase) -> tuple[SchedulerAction, str]:
        if phase in {MarketSessionPhase.WEEKEND, MarketSessionPhase.HOLIDAY}:
            return SchedulerAction.SKIP_DAY, phase.value.lower()

        if phase == MarketSessionPhase.PRE_MARKET:
            if not self.state.session_prepared:
                return SchedulerAction.PREPARE, "pre_market_initialization"
            return SchedulerAction.WAIT, "pre_market_already_prepared"

        if phase == MarketSessionPhase.REGULAR:
            if not self.state.session_active:
                return SchedulerAction.START_SESSION, "regular_session_open"
            return SchedulerAction.RUN_CYCLE, "regular_session_cycle"

        if phase == MarketSessionPhase.AFTER_HOURS:
            if self.state.session_active:
                return SchedulerAction.CLOSE_SESSION, "regular_session_closed"
            return SchedulerAction.WAIT, "after_hours_session_inactive"

        if self.state.session_active:
            return SchedulerAction.CLOSE_SESSION, "closed_market_active_session"

        return SchedulerAction.WAIT, "market_closed"

    def _next_wakeup(self, phase: MarketSessionPhase) -> int:
        if phase == MarketSessionPhase.REGULAR:
            return self.config.cycle_interval_seconds
        if phase == MarketSessionPhase.PRE_MARKET:
            return self.config.pre_market_poll_seconds
        return self.config.closed_poll_seconds
