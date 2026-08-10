from __future__ import annotations
import argparse
from pathlib import Path
from .ml_feature_drift_v2_2_15 import MLFeatureDriftMonitorV2215

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("evaluate","status"),default="evaluate")
    a=p.parse_args()
    c=MLFeatureDriftMonitorV2215(Path(a.root))
    r=c.evaluate() if a.mode=="evaluate" else c.status()
    print("=== V2.2.15 ML FEATURE DRIFT ===")
    for k in (
        "status","training_unique_feature_rows","current_unique_feature_rows",
        "feature_count","overall_drift_status","drift_interpretation_ready",
        "high_drift_features","medium_drift_features","research_only",
        "automatic_retraining_allowed","automatic_model_replacement_allowed",
        "execution_change_allowed","selector_modified","threshold_modified",
        "broker_network_used","orders_submitted","live_trading"
    ):
        if k in r:
            print(f"{k.upper()}: {r[k]}")
    if r.get("features"):
        print("FEATURE DRIFT:")
        for name,v in r["features"].items():
            print(
                f" {name}: severity={v['severity']} "
                f"mean_z={v['mean_shift_training_std_units']} "
                f"median_iqr={v['median_shift_training_iqr_units']} "
                f"std_ratio={v['current_to_training_std_ratio']}"
            )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
