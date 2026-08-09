from __future__ import annotations

import argparse

from .manual_approval_record_expiration_guard_v2_1_19 import (
    ManualApprovalRecordExpirationGuardV2119,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--evidence-key")
    a=p.parse_args()

    evidence_key=(a.evidence_key or input("Evidence key: ")).strip()

    r=ManualApprovalRecordExpirationGuardV2119(
        a.root
    ).validate_approval(evidence_key)

    print("V2.1.19 APPROVAL VALIDATION")
    print("STATUS:",r["status"])
    print("EVIDENCE KEY:",r["evidence_key"])
    print(
        "READY FOR ONE-TIME MANUAL SANDBOX HANDOFF:",
        r["ready_for_one_time_manual_sandbox_handoff"],
    )
    print("REASONS:",r.get("reasons",[]))
    print("APPROVAL CONSUMED:",r.get("approval_consumed"))
    print("USAGE COUNT:",r.get("usage_count"))
    print("AUTO SANDBOX EXECUTION:",r["automatic_sandbox_execution_allowed"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
