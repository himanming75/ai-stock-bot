from __future__ import annotations
from typing import Any

TERMINAL = {"FILLED", "CANCELED", "REJECTED", "EXPIRED"}
TRANSITIONS = {
    "NEW": {"PENDING", "REJECTED", "CANCELED"},
    "PENDING": {"ACCEPTED", "REJECTED", "CANCELED", "EXPIRED"},
    "ACCEPTED": {"PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED", "REPLACED"},
    "PARTIALLY_FILLED": {"PARTIALLY_FILLED", "FILLED", "CANCELED", "EXPIRED", "REPLACED"},
    "REPLACED": {"ACCEPTED", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"},
    "FILLED": set(),
    "CANCELED": set(),
    "REJECTED": set(),
    "EXPIRED": set(),
}

def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())

def transition(order: dict[str, Any], target: str) -> dict[str, Any]:
    current = str(order.get("state", "NEW"))
    if current == target:
        return {"allowed": target == "PARTIALLY_FILLED", "current": current, "target": target}
    allowed = can_transition(current, target)
    return {"allowed": allowed, "current": current, "target": target}
