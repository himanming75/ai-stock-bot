from __future__ import annotations
import argparse
from pathlib import Path
from .training_dataset_builder_v2_2_9 import TrainingDatasetBuilderV229

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("build","status"),default="build")
    a=p.parse_args()
    c=TrainingDatasetBuilderV229(Path(a.root))
    r=c.build() if a.mode=="build" else c.status()

    print("=== V2.2.9 TRAINING DATASET BUILDER ===")
    for key in (
        "status","source_exists","source_rows",
        "source_unique_market_dates","unique_market_dates",
        "total_matrix_rows_across_horizons",
        "dataset_ready","minimum_rows_for_ready",
        "broker_network_used","orders_submitted","live_trading",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    if r.get("artifacts"):
        for h,data in r["artifacts"].items():
            print(
                f"{h}: train={data['train']['rows']} "
                f"validation={data['validation']['rows']} "
                f"test={data['test']['rows']}"
            )
    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0

if __name__=="__main__":
    raise SystemExit(main())
