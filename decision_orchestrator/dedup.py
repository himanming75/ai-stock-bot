from __future__ import annotations
import hashlib
import json
from typing import Any

def plan_key(plan: dict[str, Any]) -> str:
    payload = {
        "strategy_id": plan.get("strategy_id"),
        "symbol": plan.get("symbol"),
        "side": plan.get("side"),
        "quantity": plan.get("quantity"),
        "reference_price": plan.get("reference_price"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def apply_duplicate_protection(
    plans: list[dict[str, Any]],
    prior_keys: set[str],
) -> list[dict[str, Any]]:
    seen = set(prior_keys)
    output = []
    for plan in plans:
        item = dict(plan)
        key = plan_key(item)
        item["plan_key"] = key
        if key in seen and item.get("state") == "PLANNED":
            item["state"] = "BLOCKED_DUPLICATE"
            item["skip_reason"] = "DUPLICATE_PLAN_KEY"
        seen.add(key)
        output.append(item)
    return output
