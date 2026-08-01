from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .models import MarketSessionPhase


@dataclass(frozen=True)
class TradingCalendarPolicy:
    timezone_name: str = "America/New_York"
    pre_market_open: time = time(4, 0)
    regular_open: time = time(9, 30)
    regular_close: time = time(16, 0)
    after_hours_close: time = time(20, 0)
    holidays: frozenset[date] = field(default_factory=frozenset)

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def localize(self, moment: datetime) -> datetime:
        if moment.tzinfo is None:
            raise ValueError("scheduler datetime must be timezone-aware")
        return moment.astimezone(self.timezone)

    def phase_at(self, moment: datetime) -> MarketSessionPhase:
        local = self.localize(moment)
        if local.weekday() >= 5:
            return MarketSessionPhase.WEEKEND
        if local.date() in self.holidays:
            return MarketSessionPhase.HOLIDAY

        current = local.timetz().replace(tzinfo=None)
        if current < self.pre_market_open:
            return MarketSessionPhase.CLOSED
        if current < self.regular_open:
            return MarketSessionPhase.PRE_MARKET
        if current < self.regular_close:
            return MarketSessionPhase.REGULAR
        if current < self.after_hours_close:
            return MarketSessionPhase.AFTER_HOURS
        return MarketSessionPhase.CLOSED

    def session_date(self, moment: datetime) -> date:
        return self.localize(moment).date()
