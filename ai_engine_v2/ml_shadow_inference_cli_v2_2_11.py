from __future__ import annotations
import argparse
from pathlib import Path
from .ml_shadow_inference_v2_2_11 import MLShadowInferenceV2211

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("preflight","run","status"),default="run")
    a=p.parse_args()
    c=MLShadowInferenceV2211(Path(a.root))
    if a.mode=="preflight":
        r=c.preflight()
    elif a.mode=="status":
        r=c.status()
    else:
        r=c.run()

    print("=== V2.2.11 ML SHADOW INFERENCE ===")
    for key in (
        "status","ml_dependencies_available","symbol_count",
        "best_shadow_research_horizon",
        "feature_engineering_reused_from_v2_2_8_1",
        "model_training_reused_from_v2_2_10",
        "shadow_only","execution_selector_modified",
        "automatic_promotion","broker_network_used",
        "paper_orders_submitted","live_orders_submitted","live_trading",
        "new_ledger_row",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")
    if r.get("research_rank"):
        print("RESEARCH RANK:")
        for row in r["research_rank"][:10]:
            print(
                f" {row['symbol']} | {row['horizon']} | "
                f"{row['direction']} | confidence={row['confidence']} | "
                f"edge_ready={row['edge_ready']}"
            )
    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0

if __name__=="__main__":
    raise SystemExit(main())
