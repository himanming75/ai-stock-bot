from __future__ import annotations
import math
from typing import Any

def quantity(position: dict[str, Any], policy: dict[str, Any], reason: str) -> float:
    total = float(position.get("quantity", 0) or 0)
    if reason in {"STOP_LOSS", "TRAILING_STOP", "BREAK_EVEN", "TIME_EXIT", "KILL_SWITCH", "RISK_EXIT"}:
        return total
    pct = float(policy.get("scale_out_pct", 100) or 100) / 100
    return min(total, max(1.0, float(math.floor(total * pct)))) if total > 0 else 0.0
