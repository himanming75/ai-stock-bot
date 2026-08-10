from __future__ import annotations
import argparse
from pathlib import Path
from .ml_prediction_outcome_v2_2_12 import MLPredictionOutcomeResolverV2212

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("preflight","resolve","metrics","status"),default="resolve")
    a=p.parse_args()
    c=MLPredictionOutcomeResolverV2212(Path(a.root))
    if a.mode=="preflight":
        r=c.preflight()
    elif a.mode=="metrics":
        r=c.build_metrics()
    elif a.mode=="status":
        r=c.status()
    else:
        r=c.resolve()

    print("=== V2.2.12 ML PREDICTION OUTCOME ===")
    for key in (
        "status","candidate_predictions","new_resolved_outcomes",
        "waiting_for_future_marks","total_resolved_outcomes",
        "shadow_only","broker_network_used","paper_orders_submitted",
        "live_orders_submitted","execution_selector_modified",
        "automatic_promotion","live_trading",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    hm=r.get("horizon_metrics") or r.get("horizons")
    if hm:
        print("HORIZON METRICS:")
        for h,v in hm.items():
            print(
                f" {h}: resolved={v['resolved_count']} "
                f"accuracy={v['direction_accuracy_pct']}% "
                f"edge_ready={v['edge_ready_count']} "
                f"edge_accuracy={v['edge_ready_accuracy_pct']}%"
            )
    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0

if __name__=="__main__":
    raise SystemExit(main())
