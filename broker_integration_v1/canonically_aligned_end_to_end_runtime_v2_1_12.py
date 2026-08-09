from __future__ import annotations

from decimal import Decimal

from .bootstrap_live_continuity_validation_v2_1_9 import (
    BootstrapLiveContinuityValidatorV219,
)
from .canonically_aligned_sandbox_bridge_v2_1_11 import (
    CanonicallyAlignedSandboxBridgeV2111,
)


class CanonicallyAlignedEndToEndRuntimeV2112:
    """
    End-to-end orchestration only.

    Existing chain reused:
      Alpaca historical bootstrap (V2.1.8.2)
      -> signal pipeline (V2.1.7/V79)
      -> canonical alignment (V2.1.11)
      -> eligible-signal bridge (V2.1.10)
      -> bounded E*TRADE Sandbox controller (V2.1.4)

    This class does not create broker transports.
    """

    def __init__(
        self,
        symbols,
        bootstrap_bars_per_symbol=3,
        validator=None,
        aligned_bridge=None,
    ):
        self.symbols=sorted({
            str(x).upper().strip()
            for x in symbols
            if str(x).strip()
        })
        if not self.symbols:
            raise ValueError("At least one symbol is required.")

        self.bootstrap_bars_per_symbol=int(
            bootstrap_bars_per_symbol
        )
        if self.bootstrap_bars_per_symbol < 3:
            raise ValueError(
                "bootstrap_bars_per_symbol must be >= 3"
            )

        self.validator=(
            validator
            or BootstrapLiveContinuityValidatorV219(
                self.symbols,
                bootstrap_bars_per_symbol=
                    self.bootstrap_bars_per_symbol,
            )
        )
        self.aligned_bridge=(
            aligned_bridge
            or CanonicallyAlignedSandboxBridgeV2111()
        )

    def build_runtime_plan(self,quantity=Decimal("1")):
        baseline=self.validator.bootstrap_only(
            quantity=Decimal(str(quantity))
        )
        signal_result=baseline["signal_result"]

        aligned_plan=self.aligned_bridge.build_plan(
            signal_result
        )

        return {
            "stage":
                "BROKER_INTEGRATION_V2_1_12_CANONICALLY_ALIGNED_END_TO_END_SANDBOX_RUNTIME",
            "status":
                "PASS_END_TO_END_PLAN_NO_ORDER"
                if aligned_plan["hold_only"]
                else "PASS_END_TO_END_PLAN_ELIGIBLE_SANDBOX",
            "symbols":self.symbols,
            "bootstrap_status":baseline["status"],
            "bootstrap_counts":baseline["bootstrap_counts"],
            "signal_result":signal_result,
            "canonical_gate_aligned":
                aligned_plan["canonical_gate_aligned"],
            "canonical_gate_alignment":
                aligned_plan["canonical_gate_alignment"],
            "eligible_signal_count":
                aligned_plan["eligible_signal_count"],
            "eligible_signals":
                aligned_plan["signals"],
            "hold_only":aligned_plan["hold_only"],
            "requires_etrade_oauth":
                not aligned_plan["hold_only"],
            "requires_explicit_sandbox_confirmation":
                not aligned_plan["hold_only"],
            "sandbox_only":True,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
            "profitability_validated":False,
        }

    def execute_sandbox(
        self,
        *,
        plan,
        account_id_key,
        cycle_engine,
        root,
        cooldown_seconds=30,
        sleep_fn=None,
    ):
        if not plan.get("canonical_gate_aligned"):
            raise RuntimeError(
                "Canonical alignment is required before Sandbox execution."
            )

        signal_result=plan["signal_result"]

        kwargs={
            "signal_result":signal_result,
            "account_id_key":account_id_key,
            "cycle_engine":cycle_engine,
            "root":root,
            "cooldown_seconds":int(cooldown_seconds),
        }
        if sleep_fn is not None:
            kwargs["sleep_fn"]=sleep_fn

        result=self.aligned_bridge.execute(**kwargs)
        result["stage"]=(
            "BROKER_INTEGRATION_V2_1_12_CANONICALLY_ALIGNED_END_TO_END_SANDBOX_RUNTIME"
        )
        result["end_to_end_runtime"]=True
        result["canonical_gate_aligned"]=True
        result["sandbox_only"]=True
        result["production_order_submission"]=False
        result["live_trading"]=False
        return result
