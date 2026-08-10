from __future__ import annotations
import argparse
from pathlib import Path
from .ml_confidence_calibration_v2_2_14 import MLConfidenceCalibrationV2214

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("evaluate","status"),default="evaluate")
    a=p.parse_args()
    c=MLConfidenceCalibrationV2214(Path(a.root))
    r=c.evaluate() if a.mode=="evaluate" else c.status()
    print("=== V2.2.14 ML CONFIDENCE CALIBRATION ===")
    for k in (
        "status","total_probability_outcomes","research_ready_horizons",
        "calibration_interpretation_ready","research_only",
        "execution_use_allowed","selector_modified","threshold_modified",
        "model_modified","model_promotion_allowed","broker_network_used",
        "orders_submitted","live_trading"
    ):
        if k in r:
            print(f"{k.upper()}: {r[k]}")
    if r.get("horizons"):
        print("HORIZON CALIBRATION:")
        for h,v in r["horizons"].items():
            print(
                f" {h}: rows={v['resolved_probability_rows']} "
                f"conf={v['mean_confidence']} "
                f"acc={v['observed_accuracy']} "
                f"ece={v['expected_calibration_error']} "
                f"brier={v['mean_multiclass_brier']} "
                f"ready={v['interpretation_allowed']}"
            )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
