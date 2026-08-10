from __future__ import annotations
import argparse
from pathlib import Path
from .ml_research_readiness_v2_2_13 import MLResearchReadinessV2213

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("evaluate","status"),default="evaluate")
    a=p.parse_args()
    c=MLResearchReadinessV2213(Path(a.root))
    r=c.evaluate() if a.mode=="evaluate" else c.status()
    print("=== V2.2.13 ML RESEARCH READINESS ===")
    for k in (
        "status","total_resolved_outcomes","minimum_total_resolved_outcomes",
        "research_ready_horizons","research_comparison_ready","block_reasons",
        "selector_change_allowed","threshold_change_allowed",
        "model_promotion_allowed","paper_execution_change_allowed",
        "broker_network_used","orders_submitted","live_trading"
    ):
        if k in r: print(f"{k.upper()}: {r[k]}")
    if r.get("horizons"):
        print("HORIZON READINESS:")
        for h,v in r["horizons"].items():
            print(f" {h}: resolved={v['resolved_count']} edge={v['edge_ready_count']} ready={v['research_ready']} blocks={v['block_reasons']}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
