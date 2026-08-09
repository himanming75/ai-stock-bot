from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo


NY=ZoneInfo("America/New_York")


def ensure_utc(dt):
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def regular_session_window(now_utc=None):
    """
    Conservative clock-window classification only.
    This does NOT claim the exchange is actually open on holidays.
    """
    now_utc=ensure_utc(now_utc or datetime.now(timezone.utc))
    now_et=now_utc.astimezone(NY)

    weekday=now_et.weekday()
    regular_day=weekday < 5
    in_clock_window=(
        regular_day
        and time(9,30) <= now_et.time().replace(tzinfo=None) < time(16,0)
    )

    return {
        "now_utc":now_utc.isoformat(),
        "now_et":now_et.isoformat(),
        "weekday":weekday,
        "regular_weekday":regular_day,
        "inside_regular_clock_window":in_clock_window,
        "status":(
            "INSIDE_REGULAR_WINDOW"
            if in_clock_window
            else "OUTSIDE_REGULAR_WINDOW"
        ),
        "holiday_verified":False,
        "exchange_open_claimed":False,
    }


@dataclass(frozen=True)
class FreshnessPolicyV2114:
    max_bar_age_seconds:int=180
    max_future_skew_seconds:int=10

    def validate(self):
        if self.max_bar_age_seconds < 30:
            raise ValueError("max_bar_age_seconds must be >= 30")
        if self.max_bar_age_seconds > 3600:
            raise ValueError("max_bar_age_seconds must be <= 3600")
        if self.max_future_skew_seconds < 0:
            raise ValueError("max_future_skew_seconds must be >= 0")
        if self.max_future_skew_seconds > 300:
            raise ValueError("max_future_skew_seconds must be <= 300")
        return self


def evaluate_bar_freshness(
    symbol_timestamps,
    now_utc=None,
    policy=None,
):
    policy=(policy or FreshnessPolicyV2114()).validate()
    now_utc=ensure_utc(now_utc or datetime.now(timezone.utc))

    per_symbol={}
    all_fresh=True

    for symbol in sorted(symbol_timestamps):
        ts=symbol_timestamps[symbol]
        if ts is None:
            per_symbol[symbol]={
                "fresh":False,
                "reason":"MISSING_TIMESTAMP",
                "age_seconds":None,
                "timestamp":None,
            }
            all_fresh=False
            continue

        ts=ensure_utc(ts)
        age=(now_utc-ts).total_seconds()

        if age < -policy.max_future_skew_seconds:
            fresh=False
            reason="FUTURE_TIMESTAMP"
        elif age > policy.max_bar_age_seconds:
            fresh=False
            reason="STALE"
        else:
            fresh=True
            reason="FRESH"

        per_symbol[symbol]={
            "fresh":fresh,
            "reason":reason,
            "age_seconds":age,
            "timestamp":ts.isoformat(),
        }
        all_fresh=all_fresh and fresh

    return {
        "all_fresh":all_fresh,
        "per_symbol":per_symbol,
        "max_bar_age_seconds":policy.max_bar_age_seconds,
        "max_future_skew_seconds":policy.max_future_skew_seconds,
    }


def build_session_freshness_gate(
    symbol_timestamps,
    now_utc=None,
    policy=None,
):
    now_utc=ensure_utc(now_utc or datetime.now(timezone.utc))
    session=regular_session_window(now_utc)
    freshness=evaluate_bar_freshness(
        symbol_timestamps,
        now_utc=now_utc,
        policy=policy,
    )

    allowed=(
        session["inside_regular_clock_window"]
        and freshness["all_fresh"]
    )

    if not session["inside_regular_clock_window"]:
        status="WAITING_OUTSIDE_REGULAR_WINDOW"
    elif not freshness["all_fresh"]:
        status="BLOCK_STALE_OR_INVALID_BAR"
    else:
        status="PASS_REGULAR_WINDOW_FRESH_BARS"

    return {
        "stage":"BROKER_INTEGRATION_V2_1_14_MARKET_SESSION_FRESHNESS_GUARD",
        "status":status,
        "signal_capture_allowed":allowed,
        "sandbox_execution_candidate_allowed":False,
        "session":session,
        "freshness":freshness,
        "etrade_oauth_started":False,
        "sandbox_preview_sent":False,
        "sandbox_place_sent":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
