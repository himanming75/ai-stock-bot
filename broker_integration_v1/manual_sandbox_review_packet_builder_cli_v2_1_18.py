from __future__ import annotations

import argparse

from .manual_sandbox_review_packet_builder_v2_1_18 import (
    ManualSandboxReviewPacketBuilderV2118,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    print("V2.1.18 MANUAL SANDBOX REVIEW PACKET BUILDER")
    print("Source: V2.1.17 qualification ledger")
    print("READY rows only")
    print("Output: JSON + Markdown review packet")
    print("Manual approval recording: DISABLED")
    print("Automatic Sandbox execution: DISABLED")
    print("E*TRADE OAuth: DISABLED")
    print("Sandbox Preview/Place: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    r=ManualSandboxReviewPacketBuilderV2118(a.root).build()

    print("")
    print("=== V2.1.18 RESULT ===")
    print("STATUS:",r["status"])
    print("SOURCE ROWS:",r["source_rows"])
    print("READY ROWS:",r["ready_rows"])
    print("NEW PACKETS:",r["new_packets"])
    print("DUPLICATE PACKETS:",r["duplicate_packets"])
    print("PACKET DIRECTORY:",r["packet_directory"])
    print("MANUAL REVIEW REQUIRED:",r.get("manual_review_required",True))
    print("AUTOMATIC SANDBOX EXECUTION:",r["automatic_sandbox_execution_allowed"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    for item in r.get("generated_packets",[]):
        print("JSON PACKET:",item["json_path"])
        print("MARKDOWN PACKET:",item["markdown_path"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
