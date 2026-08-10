from __future__ import annotations
import argparse
from pathlib import Path
from .champion_challenger_outcome_comparator_v2_2_6 import (
    ChampionChallengerOutcomeComparatorV226,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    r=ChampionChallengerOutcomeComparatorV226(Path(a.root)).build()
    print("=== V2.2.6 CHAMPION VS CHALLENGER OUTCOME COMPARATOR ===")
    for key in (
        "status","actual_outcomes","comparison_snapshots",
        "bound_actual_outcomes","bound_policy_outcome_rows",
        "unbound_actual_outcomes","new_bound_policy_outcome_rows",
        "duplicate_bindings","minimum_outcome_sample",
        "counterfactual_pnl_fabricated",
        "challenger_only_outcome_method","promotion_enabled",
        "challenger_execution_enabled","execution_selector_modified",
        "broker_network_used","paper_orders_submitted",
        "live_orders_submitted",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    print("CHALLENGERS WITH OUTCOME REPORT:",len(r.get("per_challenger") or {}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
