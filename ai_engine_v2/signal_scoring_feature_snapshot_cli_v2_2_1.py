from __future__ import annotations
import argparse
from pathlib import Path

from .signal_scoring_feature_snapshot_v2_2_1 import (
    SignalScoringFeatureSnapshotV221,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    r=SignalScoringFeatureSnapshotV221(Path(a.root)).build()
    print("=== V2.2.1 AI SIGNAL SCORING + FEATURE SNAPSHOT ===")
    for key in (
        "status",
        "snapshot_rows",
        "current_selector_eligible_count",
        "new_ledger_rows",
        "duplicate_snapshot",
        "top_shadow_symbol",
        "top_shadow_quality_score",
        "shadow_quality_score_only",
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
