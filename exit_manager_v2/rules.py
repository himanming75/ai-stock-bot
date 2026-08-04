from __future__ import annotations
from typing import Any

def take_profit(position: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    entry = float(position.get("average_cost", 0) or 0)
    current = float(position.get("market_price", 0) or 0)
    target = entry * (1 + float(policy["take_profit_pct"]) / 100)
    return {"triggered": current >= target and entry > 0, "level": round(target, 6), "reason": "TAKE_PROFIT"}

def stop_loss(position: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    entry = float(position.get("average_cost", 0) or 0)
    current = float(position.get("market_price", 0) or 0)
    level = entry * (1 - float(policy["stop_loss_pct"]) / 100)
    return {"triggered": current <= level and entry > 0, "level": round(level, 6), "reason": "STOP_LOSS"}

def trailing_stop(position: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    high = float(position.get("highest_price", position.get("market_price", 0)) or 0)
    current = float(position.get("market_price", 0) or 0)
    level = high * (1 - float(policy["trailing_stop_pct"]) / 100)
    return {"triggered": current <= level and high > 0, "level": round(level, 6), "reason": "TRAILING_STOP"}

def break_even(position: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    entry = float(position.get("average_cost", 0) or 0)
    high = float(position.get("highest_price", 0) or 0)
    current = float(position.get("market_price", 0) or 0)
    activated = entry > 0 and high >= entry * (1 + float(policy["break_even_trigger_pct"]) / 100)
    return {"triggered": activated and current <= entry, "level": round(entry, 6), "reason": "BREAK_EVEN"}

def time_exit(position: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    holding = int(position.get("holding_minutes", 0) or 0)
    maximum = int(policy["maximum_holding_minutes"])
    return {"triggered": holding >= maximum, "level": maximum, "reason": "TIME_EXIT"}
