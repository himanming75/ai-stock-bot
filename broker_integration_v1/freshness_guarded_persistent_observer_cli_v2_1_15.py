from __future__ import annotations

import argparse
from decimal import Decimal

from .persistent_market_observer_v2_1_13 import (
    ObservationPolicyV2113,
)
from .market_session_freshness_guard_v2_1_14 import (
    FreshnessPolicyV2114,
)
from .session_freshness_aware_runtime_v2_1_14 import (
    SessionFreshnessAwareRuntimeV2114,
)
from .freshness_guarded_persistent_observer_v2_1_15 import (
    FreshnessGuardedPersistentObserverV2115,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--symbols",nargs="+",default=["AAPL","MSFT","SPY"])
    p.add_argument("--bootstrap-bars",type=int,default=3)
    p.add_argument("--quantity",default="1")
    p.add_argument("--max-iterations",type=int,default=30)
    p.add_argument("--interval-seconds",type=int,default=60)
    p.add_argument("--stop-after-unchanged",type=int,default=10)
    p.add_argument("--max-bar-age-seconds",type=int,default=180)
    a=p.parse_args()

    print("V2.1.15 FRESHNESS-GUARDED PERSISTENT OBSERVER")
    print("Outside regular window: REST runtime SKIPPED")
    print("Inside regular window: V2.1.14 freshness runtime REQUIRED")
    print("Eligible capture: FRESH BARS ONLY")
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

    observer=FreshnessGuardedPersistentObserverV2115(
        runtime,
        a.root,
        ObservationPolicyV2113(
            max_iterations=a.max_iterations,
            interval_seconds=a.interval_seconds,
            stop_after_unchanged=a.stop_after_unchanged,
        ),
    )

    result=observer.run(
        quantity=Decimal(a.quantity)
    )

    print("")
    print("=== V2.1.15 RESULT ===")
    print("STATUS:",result["status"])
    print("OBSERVATIONS:",result["observation_count"])
    print("WAITING SESSION:",result["waiting_session_count"])
    print("STALE BLOCK:",result["stale_block_count"])
    print("FRESH OBSERVATIONS:",result["fresh_observation_count"])
    print("ELIGIBLE CAPTURES:",result["eligible_capture_count"])
    print("MARKET DATA RUNTIME CALLS:",result["market_data_runtime_call_count"])
    print("MARKET DATA FETCH SKIPPED:",result["market_data_fetch_skipped_count"])
    print("STOPPED REASON:",result["stopped_reason"])
    print("LEDGER:",result["ledger_path"])
    print("LATEST SNAPSHOT:",result["latest_snapshot_path"])
    print("E*TRADE OAUTH STARTED:",result["etrade_oauth_started"])
    print("BROKER ORDERS:",result["broker_orders_submitted"])
    print("PROD:",result["production_order_submission"])
    print("LIVE:",result["live_trading"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
