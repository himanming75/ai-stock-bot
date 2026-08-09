from __future__ import annotations

from datetime import datetime, timezone

from .market_session_freshness_guard_v2_1_14 import (
    FreshnessPolicyV2114,
    build_session_freshness_gate,
)


def extract_latest_bar_timestamps_from_plan(plan):
    """
    V2.1.14 needs the actual latest bar timestamps.
    V2.1.12's public plan does not expose them, so this adapter accepts
    a runtime evidence map attached by the observer/runtime caller.
    """
    evidence=plan.get("market_data_evidence") or {}
    raw=evidence.get("latest_bar_timestamps") or {}

    parsed={}
    for symbol,value in raw.items():
        if isinstance(value,datetime):
            parsed[symbol]=value
        elif value:
            parsed[symbol]=datetime.fromisoformat(
                str(value).replace("Z","+00:00")
            )
        else:
            parsed[symbol]=None
    return parsed


class SessionFreshnessGuardedPlanV2114:
    def __init__(self,policy=None):
        self.policy=(policy or FreshnessPolicyV2114()).validate()

    def guard_plan(self,plan,now_utc=None):
        timestamps=extract_latest_bar_timestamps_from_plan(plan)
        symbols=list(plan.get("symbols") or [])

        for symbol in symbols:
            timestamps.setdefault(symbol,None)

        gate=build_session_freshness_gate(
            timestamps,
            now_utc=now_utc or datetime.now(timezone.utc),
            policy=self.policy,
        )

        result=dict(plan)
        result["session_freshness_gate"]=gate
        result["signal_capture_allowed_by_v2_1_14"] = (
            gate["signal_capture_allowed"]
        )

        if not gate["signal_capture_allowed"]:
            result["eligible_signal_count_before_freshness_guard"]=int(
                plan.get("eligible_signal_count",0)
            )
            result["eligible_signal_count"]=0
            result["eligible_signals"]=[]
            result["hold_only"]=True
            result["status"]="BLOCKED_BY_SESSION_FRESHNESS_GUARD"

        result["requires_etrade_oauth"]=False
        result["requires_explicit_sandbox_confirmation"]=False
        result["broker_orders_submitted"]=0
        result["production_order_submission"]=False
        result["live_trading"]=False
        return result
