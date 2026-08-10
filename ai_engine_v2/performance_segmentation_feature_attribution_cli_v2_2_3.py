from __future__ import annotations
import argparse
from pathlib import Path

from .performance_segmentation_feature_attribution_v2_2_3 import (
    PerformanceSegmentationFeatureAttributionV223,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    r=PerformanceSegmentationFeatureAttributionV223(
        Path(a.root)
    ).build()

    print("=== V2.2.3 PERFORMANCE SEGMENTATION + FEATURE ATTRIBUTION ===")
    for key in (
        "status",
        "labeled_outcomes",
        "minimum_actionable_sample",
        "calibration_ready",
        "execution_selector_modified",
        "feature_engine_modified",
        "threshold_change_recommended_from_stage",
        "broker_network_used",
        "paper_orders_submitted",
        "live_orders_submitted",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")

    overall=r.get("overall")
    if overall:
        print("OVERALL TRADES:",overall.get("trades"))
        print("OVERALL WIN RATE %:",overall.get("win_rate_pct"))
        print("OVERALL GROSS PNL:",overall.get("gross_pnl_before_fees"))
        print("OVERALL PROFIT FACTOR:",overall.get("profit_factor"))

    return 0


if __name__=="__main__":
    raise SystemExit(main())
