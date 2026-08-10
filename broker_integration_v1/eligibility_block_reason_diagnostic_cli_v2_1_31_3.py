from __future__ import annotations
import argparse
from pathlib import Path
from .eligibility_block_reason_diagnostic_v2_1_31_3 import (
    EligibilityBlockReasonDiagnosticV21313,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("run","summary"),default="run")
    a=p.parse_args()

    c=EligibilityBlockReasonDiagnosticV21313(Path(a.root))
    r=c.run() if a.mode=="run" else c.summary()

    print("=== V2.1.31.3 ELIGIBILITY BLOCK-REASON DIAGNOSTIC ===")
    print("STATUS:",r.get("status"))
    if r.get("thresholds"):
        print("CURRENT MIN CONFIDENCE:",
              r["thresholds"].get("min_confidence"))
        print("CURRENT MIN REWARD/RISK:",
              r["thresholds"].get("min_reward_risk"))

    for row in r.get("symbols") or []:
        print("")
        print(f"[{row['symbol']}] ELIGIBLE: {row['eligible']}")
        print(
            f" action={row['action']} | "
            f"confidence={row['calibrated_confidence']:.6f} "
            f"(min={row['min_confidence']:.6f}, "
            f"margin={row['confidence_margin']:+.6f}) | "
            f"RR={row['reward_risk']:.6f} "
            f"(min={row['min_reward_risk']:.6f}, "
            f"margin={row['reward_risk_margin']:+.6f})"
        )
        reasons=row.get("block_reasons") or []
        print(
            " block_reasons="
            +(",".join(reasons) if reasons else "NONE")
        )
        print(
            f" probability={row.get('probability')} | "
            f"quality_shadow={row.get('quality_score_shadow')} | "
            f"regime={row.get('market_regime')}"
        )

    print("")
    print("ELIGIBLE_COUNT:",r.get("eligible_count"))
    print("BLOCKED_COUNT:",r.get("blocked_count"))
    print("BLOCK_REASON_COUNTS:",r.get("block_reason_counts"))
    print("EXECUTION_SELECTOR_MODIFIED:",
          r.get("execution_selector_modified"))
    print("THRESHOLDS_MODIFIED:",r.get("thresholds_modified"))
    print("BROKER_NETWORK_USED:",r.get("broker_network_used"))
    print("PAPER_ORDERS_SUBMITTED:",r.get("paper_orders_submitted"))
    print("LIVE_ORDERS_SUBMITTED:",r.get("live_orders_submitted"))

    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0

if __name__=="__main__":
    raise SystemExit(main())
