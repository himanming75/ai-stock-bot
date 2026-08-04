from __future__ import annotations
from typing import Any

def build(health:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    healthy=[x for x in health.get("rows",[]) if x.get("healthy")]
    unhealthy=[x for x in health.get("rows",[]) if not x.get("healthy")]
    primary=healthy[0]["broker_id"] if healthy else None
    secondary=healthy[1]["broker_id"] if len(healthy)>1 else None
    return {
        "enabled":policy.get("failover_enabled") is True,
        "primary_read_broker":primary,
        "secondary_read_broker":secondary,
        "isolated_brokers":[x["broker_id"] for x in unhealthy],
        "read_failover_ready":bool(primary),
        "automatic_write_failover_enabled":False,
        "broker_write_enabled":False,
        "actual_live_orders_submitted":0,
    }
