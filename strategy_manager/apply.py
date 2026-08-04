from __future__ import annotations
from pathlib import Path
from typing import Any
from strategy_manager.config import load

def build_runtime_policy(root:Path)->dict[str,Any]:
    config=load(root)
    enabled=[
        name for name,value in config.get("strategies",{}).items()
        if value.get("enabled")
    ]
    return {
        "enabled_strategies":enabled,
        "symbols":config.get("symbols",[]),
        **config.get("risk",{}),
        "paper_only":True,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
    }
