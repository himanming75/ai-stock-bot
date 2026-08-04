from __future__ import annotations
from typing import Any

def evaluate(snapshots:list[dict[str,Any]],policy:dict[str,Any])->dict[str,Any]:
    rows=[]
    for s in snapshots:
        checks={
            "status_active":str(s.get("status","")).upper() in {"ACTIVE","OK","READY"},
            "read_latency_within_limit":float(s.get("read_latency_ms",0))<=float(policy["maximum_read_latency_ms"]),
            "read_only":s.get("read_only") is True,
            "orders_unsupported":s.get("supports_orders") is False,
        }
        failed=[k for k,v in checks.items() if not v]
        rows.append({
            "broker_id":s["broker_id"],
            "account_id_masked":s["account_id_masked"],
            "healthy":not failed,
            "checks":checks,
            "failed":failed,
            "read_latency_ms":s.get("read_latency_ms",0),
        })
    healthy=sum(1 for x in rows if x["healthy"])
    return {
        "healthy_broker_count":healthy,
        "unhealthy_broker_count":len(rows)-healthy,
        "passed":healthy>=int(policy["minimum_healthy_brokers"]),
        "rows":rows,
    }
