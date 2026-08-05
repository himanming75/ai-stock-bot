from __future__ import annotations
from .models import RoutingDecision


def decide_routing(score: int, critical_signal_present: bool) -> RoutingDecision:
    if critical_signal_present or score < 50:
        return RoutingDecision(
            mode="FAILSAFE_BLOCKED",
            read_allowed=False,
            write_allowed=False,
            reason="Critical health condition detected",
            recovery_required=True,
        )
    if score < 75:
        return RoutingDecision(
            mode="READ_ONLY_SAFE_MODE",
            read_allowed=True,
            write_allowed=False,
            reason="Health degraded; safe read-only mode",
            recovery_required=True,
        )
    if score < 90:
        return RoutingDecision(
            mode="READ_ONLY_DEGRADED",
            read_allowed=True,
            write_allowed=False,
            reason="Health acceptable with degraded monitoring",
            recovery_required=False,
        )
    return RoutingDecision(
        mode="READ_ONLY_NORMAL",
        read_allowed=True,
        write_allowed=False,
        reason="Health normal",
        recovery_required=False,
    )
