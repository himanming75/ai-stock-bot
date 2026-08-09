from __future__ import annotations

from .etrade_sandbox_bounded_multi_cycle_v2_1_4 import (
    BoundedCyclePolicy,
    ETradeSandboxBoundedMultiCycleController,
)


class EligibleSignalToSandboxBridgeV2110:
    """
    Thin execution bridge:
    V2.1.9/V2.1.7 signal_result decision_queue
      -> eligible SandboxCycleSignal[]
      -> existing V2.1.4 bounded Sandbox controller.

    HOLD/blocked decisions never reach the controller.
    """

    def __init__(self, controller_factory=ETradeSandboxBoundedMultiCycleController):
        self.controller_factory=controller_factory

    @staticmethod
    def extract_eligible_signals(signal_result):
        queue=(signal_result or {}).get("decision_queue") or {}
        signals=list(queue.get("signals") or [])
        eligible_count=int(queue.get("eligible_signal_count") or 0)

        if len(signals) != eligible_count:
            raise ValueError(
                "decision_queue eligible_signal_count does not match signals length"
            )

        if len(signals) > 3:
            raise ValueError("V2.1.10 cannot execute more than 3 eligible signals")

        return signals

    def build_plan(self, signal_result):
        signals=self.extract_eligible_signals(signal_result)
        return {
            "status":"PASS_ELIGIBLE_SIGNAL_PLAN",
            "eligible_signal_count":len(signals),
            "signals":signals,
            "hold_only":len(signals)==0,
            "sandbox_only":True,
            "production_order_submission":False,
            "live_trading":False,
        }

    def execute(
        self,
        *,
        signal_result,
        account_id_key,
        cycle_engine,
        root,
        cooldown_seconds=30,
        sleep_fn=None,
    ):
        signals=self.extract_eligible_signals(signal_result)

        if not signals:
            return {
                "status":"PASS_NO_ELIGIBLE_SIGNALS_NO_ORDER",
                "eligible_signal_count":0,
                "submitted_cycle_count":0,
                "successful_cycle_count":0,
                "stopped_reason":"NO_ELIGIBLE_SIGNALS",
                "sandbox_only":True,
                "real_money_moved":False,
                "production_order_submission":False,
                "live_trading":False,
            }

        policy=BoundedCyclePolicy(
            max_cycles=min(3,len(signals)),
            cooldown_seconds=int(cooldown_seconds),
            stop_on_error=True,
            duplicate_signal_guard=True,
        ).validate()

        kwargs={}
        if sleep_fn is not None:
            kwargs["sleep_fn"]=sleep_fn

        controller=self.controller_factory(
            cycle_engine,
            root,
            policy,
            **kwargs,
        )
        result=controller.run(account_id_key,signals)
        result["stage"]="BROKER_INTEGRATION_V2_1_10_ELIGIBLE_SIGNAL_TO_SANDBOX_BRIDGE"
        result["eligible_signal_count"]=len(signals)
        result["production_order_submission"]=False
        result["live_trading"]=False
        return result
