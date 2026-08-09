from __future__ import annotations

import argparse

from .evidence_qualification_sandbox_readiness_gate_v2_1_17 import (
    EvidenceQualificationSandboxReadinessGateV2117,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    print("V2.1.17 EVIDENCE QUALIFICATION + SANDBOX READINESS GATE")
    print("Source: V2.1.16 eligible evidence ledger")
    print("Result: READY_FOR_MANUAL_SANDBOX_REVIEW / NOT_READY")
    print("Automatic Sandbox execution: DISABLED")
    print("Market data fetch: NONE")
    print("E*TRADE OAuth: DISABLED")
    print("Sandbox Preview/Place: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    r=EvidenceQualificationSandboxReadinessGateV2117(
        a.root
    ).evaluate()

    print("")
    print("=== V2.1.17 RESULT ===")
    print("STATUS:",r["status"])
    print("SOURCE LEDGER:",r["source_ledger"])
    print("SOURCE ROWS:",r["source_rows"])
    print("READY ROWS:",r["ready_rows"])
    print("NOT READY ROWS:",r["not_ready_rows"])
    print("NEW QUALIFICATION ROWS:",r["new_qualification_rows"])
    print("DUPLICATE QUALIFICATION ROWS:",r["duplicate_qualification_rows"])
    print("QUALIFICATION LEDGER:",r["qualification_ledger"])
    print("LATEST QUALIFICATION:",r.get("latest_qualification"))
    print("MANUAL REVIEW REQUIRED:",r["manual_review_required"])
    print(
        "AUTOMATIC SANDBOX EXECUTION:",
        r["automatic_sandbox_execution_allowed"],
    )
    print("E*TRADE OAUTH STARTED:",r.get("etrade_oauth_started",False))
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
