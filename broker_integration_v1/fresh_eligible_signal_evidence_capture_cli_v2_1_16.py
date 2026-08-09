from __future__ import annotations

import argparse

from .fresh_eligible_signal_evidence_capture_v2_1_16 import (
    FreshEligibleSignalEvidenceCaptureV2116,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    print("V2.1.16 FRESH ELIGIBLE SIGNAL EVIDENCE CAPTURE")
    print("Source: V2.1.15 observation ledger")
    print("Filter: OBSERVED_FRESH + eligible only")
    print("Market data fetch: NONE")
    print("E*TRADE OAuth: DISABLED")
    print("Sandbox Preview/Place: DISABLED")
    print("PROD orders: LOCKED")
    print("Live trading: LOCKED")

    r=FreshEligibleSignalEvidenceCaptureV2116(
        a.root
    ).capture()

    print("")
    print("=== V2.1.16 RESULT ===")
    print("STATUS:",r["status"])
    print("SOURCE LEDGER:",r["source_ledger"])
    print("SOURCE ROWS:",r["source_rows"])
    print("ELIGIBLE ROWS FOUND:",r["eligible_rows_found"])
    print("NEW EVIDENCE ROWS:",r["new_evidence_rows"])
    print("DUPLICATE EVIDENCE ROWS:",r["duplicate_evidence_rows"])
    print("EVIDENCE LEDGER:",r["evidence_ledger"])
    print("LATEST EVIDENCE:",r.get("latest_evidence"))
    print("E*TRADE OAUTH STARTED:",r.get("etrade_oauth_started",False))
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
