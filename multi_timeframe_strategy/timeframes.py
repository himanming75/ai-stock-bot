from __future__ import annotations
from typing import Any

def profile_for(timeframe: str, policy: dict[str, Any]) -> str | None:
    for name, profile in policy.get("profiles", {}).items():
        if profile.get("enabled") and timeframe in profile.get("timeframes", []):
            return name
    return None

def enrich(signal: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    profile_name = profile_for(str(signal.get("timeframe", "")), policy)
    if not profile_name:
        return {**signal, "eligible": False, "rejection_reason": "UNSUPPORTED_TIMEFRAME"}
    profile = policy["profiles"][profile_name]
    confidence = float(signal.get("confidence", 0) or 0)
    eligible = confidence >= float(profile["minimum_confidence"])
    return {
        **signal,
        "profile": profile_name,
        "maximum_holding_minutes": profile["maximum_holding_minutes"],
        "risk_per_trade_pct": profile["risk_per_trade_pct"],
        "capital_weight_pct": profile["capital_weight_pct"],
        "eligible": eligible,
        "rejection_reason": "" if eligible else "CONFIDENCE_BELOW_PROFILE_MINIMUM",
    }
