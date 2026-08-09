from __future__ import annotations

import argparse

from .continuous_bounded_paper_session_rollover_v2_1_28 import (
    ContinuousBoundedPaperSessionRolloverV2128,
    CONTINUOUS_SESSION_CONFIRMATION,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=["DRY","PAPER"],default="DRY")
    p.add_argument("--confirmation",default="")
    p.add_argument("--max-round-trips",type=int,default=2)
    p.add_argument("--max-supervisor-cycles",type=int,default=20)
    p.add_argument("--interval-seconds",type=int,default=30)
    p.add_argument("--local-status",action="store_true")
    p.add_argument("--rollover-plan",action="store_true")
    a=p.parse_args()

    print("V2.1.28 CONTINUOUS BOUNDED PAPER SESSION + ROLLOVER")
    print("V2.1.26 full round-trip: REUSED")
    print("V2.1.27 final reconciliation: REUSED")
    print("New entry engine: NO")
    print("New exit engine: NO")
    print("Historical ledgers: PRESERVED")
    print("Default max completed round-trips/session: 2")
    print("Live trading: LOCKED")
    print("Mode:",a.mode)

    c=ContinuousBoundedPaperSessionRolloverV2128(a.root)

    if a.local_status:
        r=c.local_status()
    elif a.rollover_plan:
        r=c.build_rollover_plan()
    else:
        r=c.run(
            mode=a.mode,
            confirmation=a.confirmation,
            max_completed_round_trips=a.max_round_trips,
            max_supervisor_cycles=a.max_supervisor_cycles,
            interval_seconds=a.interval_seconds,
        )

    print("\n=== V2.1.28 RESULT ===")
    for k in (
        "status","mode","stop_reason",
        "supervisor_cycles_completed",
        "max_completed_round_trips",
        "completed_round_trips_this_session",
        "new_completed_round_trip_ids",
        "rollover_allowed",
        "round_trip_id",
        "broker_network_used",
        "paper_orders_submitted",
        "live_orders_submitted",
        "live_orders",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    if (
        r.get("status")
        =="BLOCKED_CONTINUOUS_SESSION_CONFIRMATION_REQUIRED"
    ):
        print(
            "Required confirmation:",
            CONTINUOUS_SESSION_CONFIRMATION,
        )

    return 0


if __name__=="__main__":
    raise SystemExit(main())
