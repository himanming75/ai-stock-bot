from __future__ import annotations

from .strategies import STRATEGY_TYPES


def build_registry(config: dict) -> tuple[list, list[str]]:
    strategies = []
    blockers = []
    seen = set()
    for item in config.get("strategies", []):
        name = str(item.get("name", ""))
        if name in seen:
            blockers.append(f"DUPLICATE_STRATEGY:{name}")
            continue
        seen.add(name)
        if name not in STRATEGY_TYPES:
            blockers.append(f"UNKNOWN_STRATEGY:{name}")
            continue
        if item.get("enabled") is not True:
            continue
        strategies.append(
            {
                "name": name,
                "weight": str(item.get("weight", "1")),
                "config": dict(item.get("config", {})),
                "instance": STRATEGY_TYPES[name](),
            }
        )
    if not strategies:
        blockers.append("NO_ENABLED_STRATEGIES")
    return strategies, blockers
