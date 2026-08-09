from __future__ import annotations

import argparse
from .canonical_reward_risk_provenance_bridge_v2_1_20 import (
    CanonicalRewardRiskProvenanceBridgeV2120,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    print("V2.1.20 CANONICAL REWARD/RISK PROVENANCE BRIDGE")
    print("V2.1.16 evidence: READ-ONLY SOURCE")
    print("Canonical source: existing real-market multi-timeframe shadow")
    print("RR formula recomputation: DISABLED")
    print("Canonical confidence: 0.75")
    print("Canonical min RR: 1.0")
    print("E*TRADE OAuth: DISABLED")
    print("Sandbox Preview/Place: DISABLED")
    print("Broker orders: DISABLED")
    print("PROD: LOCKED")
    print("LIVE: LOCKED")

    r=CanonicalRewardRiskProvenanceBridgeV2120(a.root).build()
    print("")
    print("=== V2.1.20 RESULT ===")
    for k in (
        "status","reason","source_rows","new_rows","duplicate_rows","blocked_rows",
        "output_ledger","latest_output","reward_risk_formula_recomputed",
        "market_data_fetch_from_stage","broker_orders_submitted",
        "production_order_submission","live_trading",
    ):
        if k in r:
            print(k.upper()+":",r[k])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
