from pathlib import Path
from decimal import Decimal
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.canonical_gate_alignment_v2_1_11 import (
    build_canonical_gate_alignment_v2_1_11,
    CANONICAL_SIGNAL_MIN_CONFIDENCE,
    CANONICAL_PROMOTION_MIN_COMPARISONS,
)
from broker_integration_v1.canonically_aligned_sandbox_bridge_v2_1_11 import (
    CanonicallyAlignedSandboxBridgeV2111,
)

class TestV2111(unittest.TestCase):
    def test_canonical_values(self):
        self.assertEqual(
            CANONICAL_SIGNAL_MIN_CONFIDENCE,
            Decimal("0.60"),
        )
        self.assertEqual(
            CANONICAL_PROMOTION_MIN_COMPARISONS,
            20,
        )

    def test_alignment_passes(self):
        r=build_canonical_gate_alignment_v2_1_11()
        self.assertTrue(r["aligned"])
        self.assertEqual(
            r["status"],
            "PASS_CANONICAL_GATE_ALIGNMENT",
        )
        self.assertFalse(r["production_order_post_allowed"])
        self.assertFalse(r["live_trading_enabled"])

    def test_hold_plan_stays_zero_order(self):
        signal_result={
            "decision_queue":{
                "signals":[],
                "eligible_signal_count":0,
                "hold_or_block_count":3,
                "max_signals":3,
            }
        }
        p=CanonicallyAlignedSandboxBridgeV2111().build_plan(
            signal_result
        )
        self.assertTrue(p["hold_only"])
        self.assertTrue(p["canonical_gate_aligned"])

if __name__=="__main__":
    unittest.main()
