from __future__ import annotations

import argparse

from .full_alpaca_paper_round_trip_cycle_v2_1_26 import (
    FullAlpacaPaperRoundTripCycleV2126,
    FULL_CYCLE_CONFIRMATION,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=["DRY","PAPER"],default="DRY")
    p.add_argument("--confirmation",default="")
    p.add_argument("--max-cycles",type=int,default=3)
    p.add_argument("--interval-seconds",type=int,default=30)
    p.add_argument("--lifecycle-cycles",type=int,default=12)
    p.add_argument("--recover-local",action="store_true")
    a=p.parse_args()

    print("V2.1.26 FULL ALPACA PAPER ROUND-TRIP CYCLE")
    print("V2.1.21 validator: REUSED")
    print("V2.1.22 Paper entry: REUSED")
    print("V2.1.23 lifecycle: REUSED")
    print("V2.1.25 Paper exit/recovery: REUSED")
    print("Max Paper entries/cycle: 1")
    print("Max Paper exits/cycle: 1")
    print("Live trading: LOCKED")
    print("Mode:",a.mode)

    c=FullAlpacaPaperRoundTripCycleV2126(a.root)

    if a.recover_local:
        r=c.local_recovery_snapshot()
    else:
        r=c.run(
            mode=a.mode,
            confirmation=a.confirmation,
            max_cycles=a.max_cycles,
            interval_seconds=a.interval_seconds,
            lifecycle_cycles=a.lifecycle_cycles,
        )

    print("\n=== V2.1.26 RESULT ===")
    for k in (
        "status","mode","cycles_completed","stop_reason",
        "paper_entry_count","paper_exit_count","live_order_count",
        "maximum_paper_entries_per_cycle","maximum_paper_exits_per_cycle",
        "broker_network_used",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    if r.get("status")=="BLOCKED_FULL_CYCLE_CONFIRMATION_REQUIRED":
        print("Required confirmation:",FULL_CYCLE_CONFIRMATION)

    return 0


if __name__=="__main__":
    raise SystemExit(main())
