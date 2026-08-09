from __future__ import annotations

import argparse
from decimal import Decimal

from .historical_bootstrap_live_continuation_v2_1_8 import HistoricalBootstrapLiveContinuationV218


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",nargs="+",default=["AAPL","MSFT","SPY"])
    p.add_argument("--bars-per-symbol",type=int,default=3)
    p.add_argument("--quantity",default="1")
    p.add_argument("--live-continuation",action="store_true")
    p.add_argument("--live-timeout-seconds",type=int,default=120)
    a=p.parse_args()

    print("V2.1.8 HISTORICAL BOOTSTRAP + LIVE CONTINUATION")
    print("Alpaca REST bootstrap: READ-ONLY")
    print("Broker order submission: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    o=HistoricalBootstrapLiveContinuationV218(
        a.symbols,
        bars_per_symbol=a.bars_per_symbol,
    )

    print("")
    print("=== HISTORICAL BOOTSTRAP ===")
    boot=o.bootstrap_signal(quantity=Decimal(a.quantity))
    print("STATUS:",boot["status"])
    print("BAR COUNTS:",boot["bar_counts"])
    for rec in boot["signal_result"]["recommendations"]:
        print(
            rec["symbol"],
            rec["action"],
            "confidence="+str(rec["confidence"]),
        )
    print(
        "ELIGIBLE SIGNALS:",
        boot["signal_result"]["decision_queue"]["eligible_signal_count"],
    )
    print("BROKER ORDERS:",boot["broker_orders_submitted"])

    if not a.live_continuation:
        print("LIVE CONTINUATION: SKIPPED")
        return 0

    print("")
    print("=== LIVE CONTINUATION ===")
    try:
        live=o.live_continuation_once(
            timeout_seconds=a.live_timeout_seconds,
            quantity=Decimal(a.quantity),
        )
        print("STATUS:",live["status"])
        print("BAR COUNTS:",live["bar_counts"])
        print(
            "ELIGIBLE SIGNALS:",
            live["signal_result"]["decision_queue"]["eligible_signal_count"],
        )
    except TimeoutError as exc:
        print("LIVE CONTINUATION: NO CURRENT BARS BEFORE TIMEOUT")
        print(str(exc))
        print("Historical bootstrap remains valid.")
        return 0

    return 0


if __name__=="__main__":
    raise SystemExit(main())
