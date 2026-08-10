from __future__ import annotations
import argparse
from pathlib import Path
from .challenger_shadow_execution_simulator_v2_2_7 import (
    ChallengerShadowExecutionSimulatorV227,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    r=ChallengerShadowExecutionSimulatorV227(Path(a.root)).build()
    print("=== V2.2.7 CHALLENGER SHADOW EXECUTION SIMULATOR ===")
    for key in (
        "status","challenger_only_signals",
        "new_completed_shadow_round_trips",
        "new_open_shadow_positions","waiting_for_future_marks",
        "duplicate_simulations","existing_exit_rule_reused",
        "price_source","counterfactual_only","actual_broker_fills",
        "broker_network_used","paper_orders_submitted",
        "live_orders_submitted",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0

if __name__=="__main__":
    raise SystemExit(main())
