from __future__ import annotations

import argparse

from .daily_risk_budget_kill_switch_v2_1_29 import (
    DailyRiskBudgetKillSwitchV2129,
    DAILY_RISK_SESSION_CONFIRMATION,
)


CLEAR_CONFIRMATION="CLEAR_V2_1_29_KILL_SWITCH"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=["DRY","PAPER"],default="DRY")
    p.add_argument("--confirmation",default="")
    p.add_argument("--max-round-trips",type=int,default=2)
    p.add_argument("--interval-seconds",type=int,default=30)
    p.add_argument("--evaluate",action="store_true")
    p.add_argument("--engage-kill",action="store_true")
    p.add_argument("--kill-reason",default="MANUAL_KILL_SWITCH")
    p.add_argument("--clear-kill",action="store_true")
    p.add_argument("--clear-confirmation",default="")
    a=p.parse_args()

    print("V2.1.29 DAILY RISK BUDGET + KILL SWITCH")
    print("V2.1.28 continuous session: REUSED")
    print("V2.1.27 completed ledger: REUSED")
    print("Risk recheck: AFTER EACH completed round-trip")
    print("New entry/exit engine: NO")
    print("Live trading: LOCKED")

    c=DailyRiskBudgetKillSwitchV2129(a.root)

    if a.engage_kill:
        r=c.engage_kill_switch(a.kill_reason)
    elif a.clear_kill:
        if a.clear_confirmation!=CLEAR_CONFIRMATION:
            r={
                "status":"BLOCKED_KILL_SWITCH_CLEAR_CONFIRMATION_REQUIRED",
                "required_confirmation":CLEAR_CONFIRMATION,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
        else:
            r=c.clear_kill_switch()
    elif a.evaluate:
        r=c.evaluate()
    else:
        r=c.run_guarded_session(
            mode=a.mode,
            confirmation=a.confirmation,
            max_supervisor_round_trips=a.max_round_trips,
            interval_seconds=a.interval_seconds,
        )

    print("\n=== V2.1.29 RESULT ===")
    for k in (
        "status","mode","stop_reason","market_date","trading_allowed",
        "block_reasons","completed_round_trips_today",
        "daily_fill_based_gross_pnl_before_fees",
        "daily_gross_loss_budget_used_usd","consecutive_losses",
        "remaining_round_trips_today",
        "remaining_daily_gross_loss_budget_usd",
        "broker_network_used","paper_orders_submitted",
        "live_orders_submitted",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    if (
        r.get("status")
        =="BLOCKED_DAILY_RISK_SESSION_CONFIRMATION_REQUIRED"
    ):
        print(
            "Required confirmation:",
            DAILY_RISK_SESSION_CONFIRMATION,
        )
    if (
        r.get("status")
        =="BLOCKED_KILL_SWITCH_CLEAR_CONFIRMATION_REQUIRED"
    ):
        print("Required confirmation:",CLEAR_CONFIRMATION)

    return 0


if __name__=="__main__":
    raise SystemExit(main())
