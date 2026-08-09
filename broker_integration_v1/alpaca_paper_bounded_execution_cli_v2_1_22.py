from __future__ import annotations

import argparse

from .alpaca_paper_bounded_execution_bridge_v2_1_22 import (
    AlpacaPaperBoundedExecutionBridgeV2122,
    CONFIRMATION_PHRASE,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--submit-paper",action="store_true")
    p.add_argument("--confirmation",default="")
    a=p.parse_args()

    print("V2.1.22 ALPACA PAPER BOUNDED EXECUTION BRIDGE")
    print("Current V2.1.21 READY evidence: REQUIRED")
    print("Existing canonical selector: REUSED")
    print("Existing Paper service/preflight: REUSED")
    print("Existing Alpaca paper adapter: REUSED")
    print("Maximum validation notional: $25")
    print("Maximum bridge submissions per session: 1")
    print("Manual PAPER_ONLY arm token: REQUIRED FOR SUBMISSION")
    print("Live trading: HARD OFF")
    print("E*TRADE write: OFF")
    print("")

    bridge=AlpacaPaperBoundedExecutionBridgeV2122(a.root)
    if a.submit_paper:
        result=bridge.execute_once(a.confirmation)
    else:
        result=bridge.build_plan()

    print("=== V2.1.22 RESULT ===")
    for key in (
        "status","reason","evidence_key","selected_candidate",
        "maximum_notional_per_order","manual_paper_arm_required",
        "paper_order_submitted","live_order_submitted",
        "client_order_id","order","preflight",
    ):
        if key in result:
            print(key.upper()+":",result[key])

    if not a.submit_paper:
        print("")
        print("DRY PLAN ONLY. NO BROKER NETWORK OR ORDER SUBMISSION FROM THIS COMMAND.")
    elif result.get("status")=="BLOCKED_EXPLICIT_PAPER_CONFIRMATION_REQUIRED":
        print("Required confirmation:",CONFIRMATION_PHRASE)

    return 0


if __name__=="__main__":
    raise SystemExit(main())
