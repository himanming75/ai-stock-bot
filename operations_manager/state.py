from __future__ import annotations
from pathlib import Path
from operations_manager.config import load
from operations_manager.health import evaluate
from operations_manager.recovery import inspect
from operations_manager.io import load_json,tail_jsonl

def build(root:Path)->dict:
    config=load(root)
    return {
        "config":config,
        "health":evaluate(root),
        "recovery":inspect(root),
        "last_job":load_json(root/"release/v156_01_to_v160_64/actual/last_scheduled_job.json"),
        "notifications":tail_jsonl(root/"release/v156_01_to_v160_64/actual/notification_ledger.jsonl",20),
        "safety":{
            "scheduled_paper_order_submission_enabled":False,
            "live_submission_enabled":False,
            "actual_live_orders_submitted":0,
        },
    }
