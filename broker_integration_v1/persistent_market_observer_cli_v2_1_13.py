from __future__ import annotations

import argparse
from decimal import Decimal

from .canonically_aligned_end_to_end_runtime_v2_1_12 import (
    CanonicallyAlignedEndToEndRuntimeV2112,
)
from .persistent_market_observer_v2_1_13 import (
    PersistentMarketObserverV2113,
    ObservationPolicyV2113,
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
    a=p.parse_args()

    print("V2.1.13 PERSISTENT MARKET OBSERVER")
    print("Market data: ALPACA READ-ONLY")
    print("Canonical gate: REQUIRED VIA V2.1.12")
    print("E*TRADE OAuth: DISABLED IN THIS STAGE")
    print("Sandbox Preview/Place: DISABLED IN THIS STAGE")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    runtime=CanonicallyAlignedEndToEndRuntimeV2112(
        a.symbols,
        bootstrap_bars_per_symbol=a.bootstrap_bars,
    )

    observer=PersistentMarketObserverV2113(
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
    print("=== V2.1.13 RESULT ===")
    print("STATUS:",result["status"])
    print("OBSERVATIONS:",result["observation_count"])
    print("CHANGED OBSERVATIONS:",result["changed_observation_count"])
    print("ELIGIBLE OBSERVATIONS:",result["eligible_observation_count"])
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
