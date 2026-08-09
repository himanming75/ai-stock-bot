from __future__ import annotations

import argparse

from .alpaca_paper_exit_execution_recovery_guard_v2_1_25 import (
    AlpacaPaperExitExecutionRecoveryGuardV2125,
    EXIT_CONFIRMATION,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--confirmation",default="")
    p.add_argument("--recover-local",action="store_true")
    a=p.parse_args()

    print("V2.1.25 ALPACA PAPER EXIT EXECUTION + RECOVERY GUARD")
    print("V2.1.23 EXIT_READY: REQUIRED")
    print("Existing Paper service/preflight: REUSED")
    print("Existing paper=True Alpaca client: REUSED")
    print("Official close_position(symbol): USED")
    print("One-time exit fingerprint: REQUIRED")
    print("Restart duplicate-exit guard: ENABLED")
    print("Live trading: LOCKED")

    b=AlpacaPaperExitExecutionRecoveryGuardV2125(a.root)

    if a.recover_local:
        r=b.recover_state()
    elif a.execute:
        r=b.execute_once(a.confirmation)
    else:
        r=b.build_plan()

    print("\n=== V2.1.25 RESULT ===")
    for k in (
        "status","symbol","evidence_key","exit_reason",
        "exit_fingerprint_sha256","paper_exit_order_submitted",
        "live_order_submitted","recovery_guard_triggered",
        "exit_order","preflight",
    ):
        if k in r:
            print(k.upper()+":",r[k])

    if (
        r.get("status")
        =="BLOCKED_EXPLICIT_EXIT_CONFIRMATION_REQUIRED"
    ):
        print("Required confirmation:",EXIT_CONFIRMATION)

    return 0


if __name__=="__main__":
    raise SystemExit(main())
