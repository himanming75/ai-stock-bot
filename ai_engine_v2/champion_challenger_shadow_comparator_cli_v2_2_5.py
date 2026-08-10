from __future__ import annotations
import argparse
from pathlib import Path
from .champion_challenger_shadow_comparator_v2_2_5 import (
    ChampionChallengerShadowComparatorV225,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    r=ChampionChallengerShadowComparatorV225(Path(a.root)).build()
    print("=== V2.2.5 CHAMPION VS CHALLENGER SHADOW COMPARATOR ===")
    for key in (
        "status","policy_source","challengers_compared","symbols_compared",
        "comparison_rows","both_count","champion_only_count",
        "challenger_only_count","neither_count","new_ledger_rows",
        "duplicate_comparison","shadow_only",
        "challenger_execution_enabled","promotion_enabled",
        "execution_selector_modified","broker_network_used",
        "paper_orders_submitted","live_orders_submitted",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
