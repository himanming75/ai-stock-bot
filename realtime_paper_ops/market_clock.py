from __future__ import annotations
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Any


class MarketClock:
    def evaluate(
        self,
        *,
        observed_at: datetime,
        holiday: bool = False,
        early_close: bool = False,
    ) -> dict[str, Any]:
        eastern = observed_at.astimezone(ZoneInfo("America/New_York"))
        weekday_open = eastern.weekday() < 5
        open_time = time(9, 30)
        close_time = time(13, 0) if early_close else time(16, 0)
        local_time = eastern.time().replace(tzinfo=None)
        open_now = (
            weekday_open
            and not holiday
            and open_time <= local_time < close_time
        )
        phase = "CLOSED"
        if weekday_open and not holiday:
            if local_time < open_time:
                phase = "PRE_MARKET"
            elif open_now:
                phase = "REGULAR"
            elif local_time >= close_time:
                phase = "AFTER_HOURS"
        return {
            "stage": "R17_MARKET_CLOCK",
            "observed_at": observed_at.isoformat(),
            "eastern_time": eastern.isoformat(),
            "weekday_open": weekday_open,
            "holiday": holiday,
            "early_close": early_close,
            "regular_market_open": open_now,
            "market_phase": phase,
            "scheduler_execution_allowed": open_now,
            "automatic_runtime_start_enabled": False,
            "actual_market_api_used": False,
        }


class SchedulerPolicy:
    def evaluate(
        self,
        *,
        market_clock: dict[str, Any],
        p2_validated: bool,
        p3_validated: bool,
    ) -> dict[str, Any]:
        checks = {
            "market_open": market_clock.get("regular_market_open") is True,
            "p2_validated": p2_validated,
            "p3_validated": p3_validated,
            "automatic_start_disabled": True,
        }
        return {
            "stage": "R17_SCHEDULER_POLICY",
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "cycle_preview_allowed": all(checks.values()),
            "actual_cycle_started": False,
            "operator_start_required": True,
        }
