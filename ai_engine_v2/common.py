from __future__ import annotations
from dataclasses import dataclass
import math

def num(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except Exception:
        return None

def safe_status(name, status, **extra):
    result={"stage":name,"status":status}
    result.update(extra)
    return result

SAFETY_CONTRACTS={
    "shadow_only": True,
    "broker_network_used": False,
    "broker_write_performed": False,
    "order_submission_performed": False,
    "paper_parameter_change": False,
    "live_change": False,
    "automatic_promotion": False,
    "automatic_strategy_change": False,
    "production_parameter_modified": False,
    "production_selector_modified": False,
}
