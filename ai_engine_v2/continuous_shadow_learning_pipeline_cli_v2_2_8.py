from __future__ import annotations

import argparse
from pathlib import Path

from .continuous_shadow_learning_pipeline_v2_2_8 import (
    ContinuousShadowLearningPipelineV228,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("once","continuous","scorecard"),default="once")
    p.add_argument("--force",action="store_true")
    p.add_argument("--poll-seconds",type=int,default=60)
    p.add_argument("--max-runtime-seconds",type=int,default=28800)
    p.add_argument("--max-cycles",type=int,default=0)
    a=p.parse_args()

    c=ContinuousShadowLearningPipelineV228(Path(a.root))
    if a.mode=="once":
        r=c.run_cycle(force=a.force)
    elif a.mode=="scorecard":
        r=c.build_scorecard()
    else:
        r=c.run_continuous(
            poll_seconds=a.poll_seconds,
            max_runtime_seconds=a.max_runtime_seconds,
            max_cycles=a.max_cycles,
        )

    print("=== V2.2.8 CONTINUOUS AI SHADOW LEARNING PIPELINE ===")
    for key in (
        "status","cycle_id","stages_run","stages_passed",
        "cycles_completed","supervisor_polls","executed_cycles",
        "stop_reason","last_cycle_status","promotion_enabled",
        "automatic_policy_change_enabled","broker_network_used",
        "paper_orders_submitted","live_orders_submitted",
    ):
        if key in r:
            print(f"{key.upper()}: {r[key]}")

    sc=r.get("scorecard")
    if sc:
        print("ACTUAL OUTCOMES:",
              sc["champion_actual"]["completed_outcomes"])
        print("SHADOW COMPLETED:",
              sc["challenger_shadow"]["completed_counterfactual_round_trips"])
        print("CALIBRATION READY:",sc["calibration_ready"])
        print("PROMOTION EVIDENCE READY:",sc["promotion_evidence_ready"])

    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0


if __name__=="__main__":
    raise SystemExit(main())
