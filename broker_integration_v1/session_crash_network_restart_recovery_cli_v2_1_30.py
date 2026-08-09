from __future__ import annotations

import argparse

from .session_crash_network_restart_recovery_v2_1_30 import (
    SessionCrashNetworkRestartRecoveryV2130,
    RECOVERY_SESSION_CONFIRMATION,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--local-plan",action="store_true")
    p.add_argument("--reconcile",action="store_true")
    p.add_argument("--mode",choices=["DRY","PAPER"],default="DRY")
    p.add_argument("--confirmation",default="")
    p.add_argument("--max-round-trips",type=int,default=2)
    p.add_argument("--interval-seconds",type=int,default=30)
    a=p.parse_args()

    print("V2.1.30 SESSION CRASH / NETWORK / RESTART RECOVERY")
    print("V2.1.26 recovery-first state: REUSED")
    print("V2.1.27 final reconciliation: REUSED")
    print("V2.1.28 safe rollover: REUSED")
    print("V2.1.29 daily risk + kill switch: REUSED")
    print("Broker startup check: ALPACA PAPER READ-ONLY")
    print("State mismatch: FAIL CLOSED")
    print("Live trading: LOCKED")

    c=SessionCrashNetworkRestartRecoveryV2130(a.root)

    if a.local_plan:
        r=c.local_plan()
    elif a.reconcile:
        r=c.reconcile()
    else:
        r=c.recover_and_resume(
            mode=a.mode,
            confirmation=a.confirmation,
            max_round_trips=a.max_round_trips,
            interval_seconds=a.interval_seconds,
        )

    print("\n=== V2.1.30 RESULT ===")
    for k in (
        "status","mode","recovery_action","reason","mismatch_reasons",
        "attempts_used","broker_network_used","broker_write_performed",
        "paper_orders_submitted","live_orders_submitted",
        "kill_switch_engaged","delegated_v2_1_29_status",
        "delegated_stop_reason",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    if (
        r.get("status")
        =="BLOCKED_RECOVERY_SESSION_CONFIRMATION_REQUIRED"
    ):
        print("Required confirmation:",RECOVERY_SESSION_CONFIRMATION)

    return 0


if __name__=="__main__":
    raise SystemExit(main())
