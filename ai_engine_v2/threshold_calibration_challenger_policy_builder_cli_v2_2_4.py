from __future__ import annotations
import argparse
from pathlib import Path

from .threshold_calibration_challenger_policy_builder_v2_2_4 import (
    ThresholdCalibrationChallengerPolicyBuilderV224,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    r=ThresholdCalibrationChallengerPolicyBuilderV224(
        Path(a.root)
    ).build()

    print("=== V2.2.4 THRESHOLD CALIBRATION + CHALLENGER POLICY BUILDER ===")
    for key in (
        "status",
        "labeled_outcomes",
        "calibration_ready",
        "candidate_grid_size",
        "qualified_global_candidates",
        "challenger_registry_count",
        "promotion_enabled",
        "challenger_execution_enabled",
        "champion_execution_modified",
        "execution_selector_modified",
        "broker_network_used",
        "paper_orders_submitted",
        "live_orders_submitted",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")

    top=r.get("top_global_challengers") or []
    if top:
        c=top[0]
        print("TOP CHALLENGER CONFIDENCE:",c["min_confidence"])
        print("TOP CHALLENGER RR:",c["min_reward_risk"])
        print("TOP CHALLENGER SCORE:",c["challenger_score"])

    return 0


if __name__=="__main__":
    raise SystemExit(main())
