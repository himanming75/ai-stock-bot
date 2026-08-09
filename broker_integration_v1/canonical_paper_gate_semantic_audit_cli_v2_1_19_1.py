from __future__ import annotations

import argparse

from .canonical_paper_gate_semantic_audit_v2_1_19_1 import (
    run_semantic_audit_v2_1_19_1,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    r=run_semantic_audit_v2_1_19_1(a.root)

    print("V2.1.19.1 CANONICAL PAPER GATE SEMANTIC AUDIT")
    print("GENERIC E*TRADE CONFIDENCE:",r["generic_etrade_bridge_min_confidence"])
    print("CANONICAL PAPER CONFIDENCE:",r["canonical_paper_min_confidence"])
    print("CANONICAL PAPER MIN RR:",r["canonical_paper_min_reward_risk"])
    print("QUALIFICATION ROWS:",r["qualification_rows"])
    print("LEGACY QUALIFICATION ROWS:",r["legacy_qualification_rows"])
    print("LEGACY REVIEW PACKET ROWS:",r["legacy_review_packet_rows"])
    print("LEGACY APPROVAL ROWS:",r["legacy_approval_rows"])
    print("LEGACY ARTIFACTS BLOCKED:",r["legacy_artifacts_blocked_by_corrected_code"])
    print("RUNTIME DATA DELETED:",r["runtime_data_deleted"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    print("REPORT:",r["report_path"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
