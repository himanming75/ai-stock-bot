from pathlib import Path
from strategy_manager.config import load
from strategy_manager.apply import build_runtime_policy

def payload(root:Path)->dict:
    return {
        "config":load(root),
        "runtime_policy":build_runtime_policy(root),
        "live_controls_available":False,
        "actual_live_orders_submitted":0,
    }
