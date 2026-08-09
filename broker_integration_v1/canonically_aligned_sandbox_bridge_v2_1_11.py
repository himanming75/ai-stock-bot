from __future__ import annotations

from .canonical_gate_alignment_v2_1_11 import (
    require_canonical_gate_alignment_v2_1_11,
)
from .eligible_signal_to_sandbox_bridge_v2_1_10 import (
    EligibleSignalToSandboxBridgeV2110,
)


class CanonicallyAlignedSandboxBridgeV2111:
    """
    V2.1.10 execution bridge with an immutable preflight audit
    against the repository's current canonical signal/promotion/safety gates.
    """

    def __init__(self,execution_bridge=None):
        self.execution_bridge=(
            execution_bridge
            or EligibleSignalToSandboxBridgeV2110()
        )

    def build_plan(self,signal_result):
        alignment=require_canonical_gate_alignment_v2_1_11()
        plan=self.execution_bridge.build_plan(signal_result)
        plan["canonical_gate_alignment"]=alignment
        plan["canonical_gate_aligned"]=True
        plan["production_order_submission"]=False
        plan["live_trading"]=False
        return plan

    def execute(self,**kwargs):
        alignment=require_canonical_gate_alignment_v2_1_11()
        result=self.execution_bridge.execute(**kwargs)
        result["stage"]="BROKER_INTEGRATION_V2_1_11_CANONICALLY_ALIGNED_SANDBOX_BRIDGE"
        result["canonical_gate_alignment"]=alignment
        result["canonical_gate_aligned"]=True
        result["production_order_submission"]=False
        result["live_trading"]=False
        return result
