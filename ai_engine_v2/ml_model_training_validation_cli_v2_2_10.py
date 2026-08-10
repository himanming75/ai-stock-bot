from __future__ import annotations
import argparse
from pathlib import Path
from .ml_model_training_validation_v2_2_10 import (
    MLModelTrainingValidationV2210,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("preflight","train","status"),default="preflight")
    a=p.parse_args()
    c=MLModelTrainingValidationV2210(Path(a.root))
    if a.mode=="train":
        r=c.train_all()
    elif a.mode=="status":
        r=c.status()
    else:
        r=c.preflight()

    print("=== V2.2.10 ML MODEL TRAINING + VALIDATION ===")
    for key in (
        "status","dataset_ready","ml_dependencies_available",
        "training_ready","source_rows","source_unique_market_dates",
        "any_edge_ready","best_test_horizon_for_shadow_research",
        "test_set_used_for_selection","bounded_walk_forward_enabled",
        "automatic_promotion","execution_selector_modified",
        "broker_network_used","orders_submitted","live_trading",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    if r.get("horizons"):
        for h,v in r["horizons"].items():
            tm=v["test_metrics"]
            print(
                f"{h}: model={v['selected_model']} "
                f"val={v['selected_validation_score']:.6f} "
                f"delta_dummy={v['validation_improvement_over_dummy']:.6f} "
                f"test_macro_f1={tm['macro_f1']:.6f} "
                f"test_bal_acc={tm['balanced_accuracy']:.6f} "
                f"edge_ready={v['edge_ready']}"
            )
    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0

if __name__=="__main__":
    raise SystemExit(main())
