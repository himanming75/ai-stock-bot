from __future__ import annotations

import argparse
from decimal import Decimal

from .session_freshness_aware_runtime_v2_1_14 import (
    SessionFreshnessAwareRuntimeV2114,
)
from .market_session_freshness_guard_v2_1_14 import (
    FreshnessPolicyV2114,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",nargs="+",default=["AAPL","MSFT","SPY"])
    p.add_argument("--bootstrap-bars",type=int,default=3)
    p.add_argument("--quantity",default="1")
    p.add_argument("--max-bar-age-seconds",type=int,default=180)
    a=p.parse_args()

    print("V2.1.14 MARKET SESSION + FRESHNESS GUARD")
    print("Market data: ALPACA READ-ONLY")
    print("Regular-hours clock window: ADVISORY ONLY")
    print("Fresh bar required for signal capture")
    print("E*TRADE OAuth: DISABLED")
    print("Sandbox Preview/Place: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    runtime=SessionFreshnessAwareRuntimeV2114(
        a.symbols,
        bootstrap_bars_per_symbol=a.bootstrap_bars,
        freshness_policy=FreshnessPolicyV2114(
            max_bar_age_seconds=a.max_bar_age_seconds,
        ),
    )

    plan=runtime.build_runtime_plan(
        quantity=Decimal(a.quantity)
    )

    gate=plan["session_freshness_gate"]

    print("")
    print("=== SESSION WINDOW ===")
    print("STATUS:",gate["session"]["status"])
    print(
        "INSIDE REGULAR WINDOW:",
        gate["session"]["inside_regular_clock_window"],
    )
    print(
        "HOLIDAY VERIFIED:",
        gate["session"]["holiday_verified"],
    )
    print(
        "EXCHANGE OPEN CLAIMED:",
        gate["session"]["exchange_open_claimed"],
    )

    print("")
    print("=== FRESHNESS ===")
    print("ALL FRESH:",gate["freshness"]["all_fresh"])
    for symbol,row in gate["freshness"]["per_symbol"].items():
        print(
            symbol,
            "reason="+str(row["reason"]),
            "age_seconds="+str(row["age_seconds"]),
            "timestamp="+str(row["timestamp"]),
        )

    print("")
    print("=== GUARDED PLAN ===")
    print("STATUS:",plan["status"])
    print(
        "SIGNAL CAPTURE ALLOWED:",
        plan["signal_capture_allowed_by_v2_1_14"],
    )
    print("ELIGIBLE SIGNALS:",plan["eligible_signal_count"])
    print("REQUIRES E*TRADE OAUTH:",plan["requires_etrade_oauth"])
    print("BROKER ORDERS:",plan["broker_orders_submitted"])
    print("PROD:",plan["production_order_submission"])
    print("LIVE:",plan["live_trading"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
