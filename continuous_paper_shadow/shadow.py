from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from continuous_paper_shadow.io import digest

def build_shadow_records(plans:list[dict[str,Any]],mode:str)->list[dict[str,Any]]:
    rows=[]
    for p in plans:
        row={
            "shadow_id":digest({"plan":p,"mode":mode})[:24],
            "observed_at":datetime.now(timezone.utc).isoformat(),
            "symbol":p.get("symbol"),"side":p.get("side"),
            "quantity":p.get("qty"),
            "estimated_notional":p.get("estimated_notional"),
            "source_mode":mode,
            "live_order_would_be_created":True,
            "live_order_submitted":False,
            "actual_live_orders_submitted":0,
        }
        rows.append(row)
    return rows
