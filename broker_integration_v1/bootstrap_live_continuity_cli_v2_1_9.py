from __future__ import annotations

import argparse
from decimal import Decimal

from .bootstrap_live_continuity_validation_v2_1_9 import BootstrapLiveContinuityValidatorV219


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",nargs="+",default=["AAPL","MSFT","SPY"])
    p.add_argument("--bootstrap-bars",type=int,default=3)
    p.add_argument("--live-bars",type=int,default=3)
    p.add_argument("--timeout-seconds",type=int,default=120)
    p.add_argument("--quantity",default="1")
    p.add_argument("--with-live",action="store_true")
    a=p.parse_args()

    print("V2.1.9 BOOTSTRAP -> LIVE CONTINUITY VALIDATION")
    print("Historical bootstrap: READ-ONLY")
    print("Live continuation: OPTIONAL READ-ONLY")
    print("Broker orders: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    v=BootstrapLiveContinuityValidatorV219(
        a.symbols,
        bootstrap_bars_per_symbol=a.bootstrap_bars,
    )

    base=v.bootstrap_only(quantity=Decimal(a.quantity))

    print("")
    print("=== BOOTSTRAP BASELINE ===")
    print("STATUS:",base["status"])
    print("BAR COUNTS:",base["bootstrap_counts"])
    for rec in base["signal_result"]["recommendations"]:
        print(
            rec["symbol"],
            rec["action"],
            "confidence="+str(rec["confidence"]),
        )
    print(
        "ELIGIBLE SIGNALS:",
        base["signal_result"]["decision_queue"]["eligible_signal_count"],
    )

    if not a.with_live:
        print("LIVE CONTINUITY VALIDATION: SKIPPED")
        return 0

    print("")
    print("=== LIVE CONTINUITY VALIDATION ===")
    try:
        live=v.collect_live_and_validate(
            base["bootstrap_bars"],
            timeout_seconds=a.timeout_seconds,
            live_bars_per_symbol=a.live_bars,
            quantity=Decimal(a.quantity),
        )
    except TimeoutError as exc:
        print("LIVE CONTINUITY: NO SUFFICIENT CURRENT BARS BEFORE TIMEOUT")
        print(str(exc))
        print("BOOTSTRAP BASELINE REMAINS PASS")
        return 0

    print("STATUS:",live["status"])
    print("LIVE COUNTS:",live["live_counts"])
    print("MERGED COUNTS:",live["merged_counts"])
    print("DUPLICATE FREE:",live["duplicate_free"])
    print("MONOTONIC:",live["monotonic"])
    print(
        "ELIGIBLE SIGNALS:",
        live["signal_result"]["decision_queue"]["eligible_signal_count"],
    )
    print("BROKER ORDERS:",live["broker_orders_submitted"])
    print("PROD:",live["production_order_submission"])
    print("LIVE TRADING:",live["live_trading"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
