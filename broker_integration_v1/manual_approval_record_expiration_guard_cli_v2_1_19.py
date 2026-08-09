from __future__ import annotations

import argparse

from .manual_approval_record_expiration_guard_v2_1_19 import (
    ManualApprovalRecordExpirationGuardV2119,
    ApprovalPolicyV2119,
    APPROVAL_PHRASE,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--evidence-key")
    p.add_argument("--expires-minutes",type=int,default=15)
    a=p.parse_args()

    print("V2.1.19 MANUAL APPROVAL RECORD + EXPIRATION GUARD")
    print("Source: V2.1.18 manual review packet")
    print("Approval phrase required:",APPROVAL_PHRASE)
    print("Default expiration: 15 minutes")
    print("One-time-use state: INITIALIZED, NOT CONSUMED")
    print("Automatic Sandbox execution: DISABLED")
    print("E*TRADE OAuth: DISABLED")
    print("Sandbox Preview/Place: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")
    print("")

    evidence_key=(a.evidence_key or input("Evidence key: ")).strip()
    phrase=input(
        f"Type {APPROVAL_PHRASE} to record approval only: "
    ).strip()

    g=ManualApprovalRecordExpirationGuardV2119(
        a.root,
        ApprovalPolicyV2119(
            expires_minutes=a.expires_minutes,
        ),
    )

    r=g.approve(
        evidence_key,
        phrase,
        approved_by="LOCAL_USER",
    )

    print("")
    print("=== APPROVAL RECORD RESULT ===")
    for key in (
        "status",
        "reason",
        "evidence_key",
        "approval_id",
        "approved_at_utc",
        "expires_at_utc",
        "approval_consumed",
        "usage_count",
        "one_time_use",
        "automatic_sandbox_execution_allowed",
        "broker_orders_submitted",
        "production_order_submission",
        "live_trading",
    ):
        if key in r:
            print(key.upper()+":",r[key])

    if r.get("status")=="PASS_MANUAL_APPROVAL_RECORDED":
        v=g.validate_approval(evidence_key)
        print("")
        print("=== CURRENT APPROVAL VALIDATION ===")
        print("STATUS:",v["status"])
        print(
            "READY FOR ONE-TIME MANUAL SANDBOX HANDOFF:",
            v["ready_for_one_time_manual_sandbox_handoff"],
        )
        print("REASONS:",v["reasons"])
        print("AUTO SANDBOX EXECUTION:",v["automatic_sandbox_execution_allowed"])
        print("BROKER ORDERS:",v["broker_orders_submitted"])
        print("PROD:",v["production_order_submission"])
        print("LIVE:",v["live_trading"])

    return 0


if __name__=="__main__":
    raise SystemExit(main())
