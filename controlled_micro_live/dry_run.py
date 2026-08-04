from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from controlled_micro_live.io import write_json,digest
from controlled_micro_live.config import load as load_policy

def build(root:Path,candidate:dict[str,Any],checks:dict[str,Any])->dict[str,Any]:
    policy=load_policy(root)
    qty=float(candidate.get("quantity",candidate.get("qty",0)) or 0)
    notional=float(candidate.get("estimated_notional",0) or 0)
    receipt={
        "receipt_type":"CONTROLLED_MICRO_LIVE_DRY_RUN",
        "receipt_id":digest({"candidate":candidate,"time":datetime.now(timezone.utc).isoformat()})[:24],
        "created_at":datetime.now(timezone.utc).isoformat(),
        "candidate":candidate,
        "checks":checks,
        "quantity":qty,
        "estimated_notional":notional,
        "within_quantity_limit":0<qty<=policy["maximum_quantity"],
        "within_notional_limit":0<notional<=policy["maximum_order_notional"],
        "dry_run_only":True,
        "broker_request_created":False,
        "live_network_attempted":False,
        "live_write_attempted":False,
        "execution_authorized":False,
        "actual_live_orders_submitted":0,
    }
    write_json(root/"release/v171_01_to_v175_64/actual/micro_live_dry_run_receipt.json",receipt)
    return receipt
