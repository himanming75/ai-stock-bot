from __future__ import annotations
from pathlib import Path
from v89_engine.io import load_json

def status(root: Path):
    multi=load_json(root/"release/v83_77_to_v83_80/actual/multi_day_paper_validation_result.json")
    completed=int(multi.get("completed_days",0)); required=int(multi.get("minimum_days",3))
    remaining=max(0,required-completed)
    return {
      "state":"FINAL_VALIDATION_READY_TO_CONTINUE" if remaining==0 else "FINAL_VALIDATION_WAITING_FOR_DAYS",
      "completed_days":completed,"required_days":required,"remaining_days":remaining,
      "requirement_met":remaining==0,
      "next_commands":[
        "RUN_V83_81_TO_V83_88_PAPER_STABILITY_RUNTIME.ps1",
        "RUN_V83_89_TO_V83_96_PERFORMANCE_READINESS.ps1",
        "RUN_V88_17_TO_V88_24_PAPER_PRODUCTION_RELEASE.ps1"
      ] if remaining==0 else ["RUN_V83_77_TO_V83_80_MULTI_DAY_PAPER_VALIDATION.ps1"]
    }
