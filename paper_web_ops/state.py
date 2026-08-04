from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from paper_web_ops.io import load_json
from paper_web_ops.settings import load as load_settings

def build(root:Path)->dict[str,Any]:
    paper=load_json(root/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json")
    shadow=load_json(root/"release/v124_01_to_v126_64/actual/continuous_paper_shadow_result.json")
    action=load_json(root/"release/v151_01_to_v155_64/actual/last_paper_web_action.json")
    settings=load_settings(root)
    account=paper.get("account_snapshot") or {
        "equity":paper.get("account_equity"),
    }
    positions=paper.get("position_snapshot",[])
    orders=paper.get("order_snapshot",[])
    clock=paper.get("clock_snapshot",{})
    return {
        "credentials":{
            "paper_key_present":bool(os.environ.get("ALPACA_PAPER_API_KEY")),
            "paper_secret_present":bool(os.environ.get("ALPACA_PAPER_SECRET_KEY")),
            "ready":bool(os.environ.get("ALPACA_PAPER_API_KEY")) and bool(os.environ.get("ALPACA_PAPER_SECRET_KEY")),
        },
        "settings":settings,
        "account":account,
        "positions":positions,
        "orders":orders,
        "market":{
            "is_open":clock.get("is_open",paper.get("market_open")),
            "timestamp":clock.get("timestamp"),
        },
        "paper_result":{
            "state":paper.get("state","NOT_AVAILABLE"),
            "status":paper.get("status"),
            "actual_paper_orders_submitted":paper.get("actual_paper_orders_submitted",0),
            "actual_live_orders_submitted":paper.get("actual_live_orders_submitted",0),
        },
        "shadow_result":{
            "state":shadow.get("state","NOT_AVAILABLE"),
            "status":shadow.get("status"),
            "signal_count":len(shadow.get("signals",[])),
            "plan_count":len(shadow.get("paper_order_plans",[])),
            "qualification":shadow.get("qualification",{}),
            "actual_paper_orders_submitted":shadow.get("actual_paper_orders_submitted",0),
            "actual_live_orders_submitted":shadow.get("actual_live_orders_submitted",0),
        },
        "last_action":action,
        "safety":{
            "paper_only":True,
            "live_network_enabled":False,
            "live_submission_enabled":False,
            "actual_live_orders_submitted":0,
        },
    }
