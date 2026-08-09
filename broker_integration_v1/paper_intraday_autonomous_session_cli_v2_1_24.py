from __future__ import annotations

import argparse

from .paper_intraday_autonomous_session_controller_v2_1_24 import (
    PaperIntradayAutonomousSessionControllerV2124,
    SESSION_CONFIRMATION,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=["DRY","PAPER"],default="DRY")
    p.add_argument("--session-confirmation",default="")
    p.add_argument("--max-cycles",type=int,default=3)
    p.add_argument("--interval-seconds",type=int,default=30)
    p.add_argument("--lifecycle-cycles",type=int,default=12)
    a=p.parse_args()

    print("V2.1.24 PAPER INTRADAY AUTONOMOUS SESSION CONTROLLER")
    print("V2.1.21 validator: REUSED")
    print("V2.1.22 bounded Paper entry: REUSED")
    print("V2.1.23 read-only lifecycle: REUSED")
    print("Maximum Paper entries/session: 1")
    print("Automatic exit order write: DISABLED")
    print("Live trading: LOCKED")
    print("Mode:",a.mode)

    r=PaperIntradayAutonomousSessionControllerV2124(a.root).run(
        mode=a.mode,
        session_confirmation=a.session_confirmation,
        max_cycles=a.max_cycles,
        interval_seconds=a.interval_seconds,
        lifecycle_cycles=a.lifecycle_cycles,
    )

    print("\n=== V2.1.24 RESULT ===")
    for k in (
        "status","session_id","mode","cycles_completed","stop_reason",
        "paper_orders_submitted","maximum_paper_orders_per_session",
        "lifecycle_monitors_run","exit_orders_submitted",
        "live_orders_submitted",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    if r.get("status")=="BLOCKED_SESSION_CONFIRMATION_REQUIRED":
        print("Required confirmation:",SESSION_CONFIRMATION)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
