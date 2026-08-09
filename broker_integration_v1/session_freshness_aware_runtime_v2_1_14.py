from __future__ import annotations

from datetime import datetime, timezone

from .canonically_aligned_end_to_end_runtime_v2_1_12 import (
    CanonicallyAlignedEndToEndRuntimeV2112,
)
from .market_session_freshness_guard_v2_1_14 import (
    FreshnessPolicyV2114,
)
from .session_freshness_guarded_plan_v2_1_14 import (
    SessionFreshnessGuardedPlanV2114,
)


def _latest_timestamps_from_runtime(runtime):
    """
    Reuse V2.1.8.2 bootstrap diagnostics after V2.1.12 builds its plan.
    No duplicate market-data fetch is performed.
    """
    validator=getattr(runtime,"validator",None)
    client=getattr(validator,"bootstrap_client",None)
    diagnostics=getattr(client,"last_diagnostics",{}) or {}
    per_symbol=diagnostics.get("symbol_diagnostics") or {}

    out={}
    for symbol,row in per_symbol.items():
        value=(row or {}).get("last_timestamp")
        out[symbol]=value
    return out


class SessionFreshnessAwareRuntimeV2114:
    """
    Safety wrapper around the existing V2.1.12 runtime.
    It reuses the timestamps already collected by V2.1.8.2 diagnostics.
    """

    def __init__(
        self,
        symbols,
        bootstrap_bars_per_symbol=3,
        base_runtime=None,
        freshness_policy=None,
    ):
        self.symbols=sorted({
            str(x).upper().strip()
            for x in symbols
            if str(x).strip()
        })
        if not self.symbols:
            raise ValueError("At least one symbol is required.")

        self.base_runtime=(
            base_runtime
            or CanonicallyAlignedEndToEndRuntimeV2112(
                self.symbols,
                bootstrap_bars_per_symbol=bootstrap_bars_per_symbol,
            )
        )

        self.guard=SessionFreshnessGuardedPlanV2114(
            freshness_policy
            or FreshnessPolicyV2114()
        )

    def build_runtime_plan(self,quantity=1,now_utc=None):
        plan=self.base_runtime.build_runtime_plan(
            quantity=quantity
        )

        timestamps=_latest_timestamps_from_runtime(
            self.base_runtime
        )

        plan=dict(plan)
        plan["market_data_evidence"]={
            "latest_bar_timestamps":timestamps,
            "source":"V2.1.8.2_BOOTSTRAP_DIAGNOSTICS_REUSED",
            "duplicate_fetch_performed":False,
        }

        guarded=self.guard.guard_plan(
            plan,
            now_utc=now_utc or datetime.now(timezone.utc),
        )

        guarded["stage"]=(
            "BROKER_INTEGRATION_V2_1_14_MARKET_SESSION_FRESHNESS_AWARE_RUNTIME"
        )
        guarded["v2_1_12_runtime_reused"]=True
        guarded["v2_1_8_2_timestamp_diagnostics_reused"]=True
        guarded["etrade_oauth_started"]=False
        guarded["sandbox_preview_sent"]=False
        guarded["sandbox_place_sent"]=False
        guarded["broker_orders_submitted"]=0
        guarded["production_order_submission"]=False
        guarded["live_trading"]=False
        return guarded
