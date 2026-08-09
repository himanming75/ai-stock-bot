from __future__ import annotations

import argparse

from .one_click_daily_paper_operation_v2_1_31 import (
    OneClickDailyPaperOperationV2131,
    DAILY_OPERATION_CONFIRMATION,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--dry-plan",action="store_true")
    p.add_argument("--paper",action="store_true")
    p.add_argument("--confirmation",default="")
    a=p.parse_args()

    print("V2.1.31 ONE-CLICK DAILY ALPACA PAPER OPERATION")
    print("V2.1.30 operational entry: REUSED")
    print("V2.1.29 daily risk: REUSED")
    print("Market-open wait: PAPER READ-ONLY")
    print("New signal/order/recovery engine: NO")
    print("Live trading: LOCKED")

    c=OneClickDailyPaperOperationV2131(a.root)

    if a.paper:
        r=c.run_paper(confirmation=a.confirmation)
    else:
        r=c.dry_plan()

    print("\n=== V2.1.31 RESULT ===")
    for k in (
        "status","mode","would_wait_for_market_open",
        "would_delegate_to_v2_1_30",
        "startup_recovery_status","startup_recovery_action",
        "market_wait_status","market_wait_polls",
        "delegated_v2_1_30_status","delegated_stop_reason",
        "new_completed_round_trip_count",
        "new_completed_round_trip_ids",
        "broker_network_used","broker_write_performed",
        "paper_orders_submitted","live_orders_submitted",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    if (
        r.get("status")
        =="BLOCKED_DAILY_OPERATION_CONFIRMATION_REQUIRED"
    ):
        print("Required confirmation:",DAILY_OPERATION_CONFIRMATION)

    return 0


if __name__=="__main__":
    raise SystemExit(main())
