from __future__ import annotations

import argparse
from decimal import Decimal

from .alpaca_readonly_current_bar_collector_v2_1_7 import (
    AlpacaReadOnlyCurrentBarCollectorV217,
    CONFIRMATION,
)
from .etrade_current_market_data_signal_bridge_v2_1_7 import (
    CurrentMarketDataSignalBridgeV217,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",nargs="+",default=["AAPL"])
    p.add_argument("--bars-per-symbol",type=int,default=3)
    p.add_argument("--timeout-seconds",type=int,default=900)
    p.add_argument("--quantity",default="1")
    p.add_argument("--confirm",required=True)
    args=p.parse_args()

    print("E*TRADE V2.1.7 CURRENT MARKET DATA -> SIGNAL")
    print("Market data source: ALPACA READ-ONLY")
    print("Broker orders from this stage: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    if args.confirm != CONFIRMATION:
        raise SystemExit("CONFIRMATION TEXT MISMATCH - NO NETWORK CONNECTION")

    collector=AlpacaReadOnlyCurrentBarCollectorV217(
        args.symbols,
        bars_per_symbol=args.bars_per_symbol,
    )

    bars,counts=collector.collect(timeout_seconds=args.timeout_seconds)
    print("BAR COUNTS:",counts)

    result=CurrentMarketDataSignalBridgeV217(
        min_bars_per_symbol=args.bars_per_symbol
    ).build_from_bars(
        bars,
        quantity=Decimal(args.quantity),
        max_signals=3,
    )

    print("")
    print("=== CURRENT MARKET SIGNAL RESULT ===")
    for rec in result["recommendations"]:
        print(
            rec["symbol"],
            rec["action"],
            "confidence="+str(rec["confidence"]),
            "score="+str(rec["source_score"]),
        )

    dq=result["decision_queue"]
    print("ELIGIBLE SIGNALS:",dq["eligible_signal_count"])
    print("HOLD/BLOCK:",dq["hold_or_block_count"])
    print("BROKER ORDERS SUBMITTED:",result["broker_orders_submitted"])
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
