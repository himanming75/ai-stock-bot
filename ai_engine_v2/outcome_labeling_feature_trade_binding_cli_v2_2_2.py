from __future__ import annotations
import argparse
from pathlib import Path

from .outcome_labeling_feature_trade_binding_v2_2_2 import (
    OutcomeLabelingFeatureTradeBindingV222,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    r=OutcomeLabelingFeatureTradeBindingV222(Path(a.root)).build()
    print("=== V2.2.2 OUTCOME LABELING + FEATURE/TRADE BINDING ===")
    for key in (
        "status",
        "completed_trade_rows",
        "feature_snapshot_rows",
        "new_labeled_outcomes",
        "new_unbound_outcomes",
        "duplicate_round_trips",
        "invalid_trade_rows",
        "latest_bound_round_trip_id",
        "pnl_recomputed",
        "feature_engine_modified",
        "execution_selector_modified",
        "broker_network_used",
        "paper_orders_submitted",
        "live_orders_submitted",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    return 0 if not str(r.get("status","")).startswith("BLOCKED_") else 2


if __name__=="__main__":
    raise SystemExit(main())
