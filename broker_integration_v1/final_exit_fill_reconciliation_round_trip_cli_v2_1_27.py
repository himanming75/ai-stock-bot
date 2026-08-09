from __future__ import annotations

import argparse

from .final_exit_fill_reconciliation_round_trip_ledger_v2_1_27 import (
    FinalExitFillReconciliationRoundTripLedgerV2127,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--reconcile",action="store_true")
    p.add_argument("--interval-seconds",type=int,default=5)
    p.add_argument("--max-cycles",type=int,default=12)
    a=p.parse_args()

    print("V2.1.27 FINAL EXIT FILL RECONCILIATION + ROUND-TRIP LEDGER")
    print("V2.1.23 actual entry fill: REUSED")
    print("V2.1.25 exit submission: REUSED")
    print("Existing Alpaca Paper read client: REUSED")
    print("Broker writes from this stage: DISABLED")
    print("Completed P&L: fill-based gross P&L before fees")
    print("Live trading: LOCKED")

    c=FinalExitFillReconciliationRoundTripLedgerV2127(a.root)
    r=(
        c.reconcile(
            interval_seconds=a.interval_seconds,
            max_cycles=a.max_cycles,
        )
        if a.reconcile
        else c.build_plan()
    )

    print("\n=== V2.1.27 RESULT ===")
    for k in (
        "status","round_trip_id","symbol","evidence_key",
        "entry_client_order_id","exit_client_order_id",
        "broker_network_used","broker_write_performed",
        "paper_orders_submitted","live_orders_submitted",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    completed=r.get("completed_round_trip")
    if completed:
        print("ENTRY FILL:",completed["entry"])
        print("EXIT FILL:",completed["exit"])
        print("HOLDING SECONDS:",completed["holding_seconds"])
        print("GROSS PNL:",completed["gross_pnl_from_fills"])
        print("RETURN %:",completed["return_pct_from_fills"])
        print("PNL SEMANTICS:",completed["pnl_semantics"])

    if not a.reconcile:
        print("\nDRY PLAN ONLY. NO BROKER NETWORK.")

    return 0


if __name__=="__main__":
    raise SystemExit(main())
