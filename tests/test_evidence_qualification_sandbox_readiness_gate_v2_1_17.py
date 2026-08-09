from pathlib import Path
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_v2_1_17 import (
    qualify_evidence_row_v2_1_17,
)
from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_status_v2_1_17 import (
    build_v2_1_17_status,
)


def row(conf="0.80",rr="1.20"):
    return {
        "evidence_key":"x",
        "observer_state":"OBSERVED_FRESH",
        "canonical_gate_aligned":True,
        "eligible_signal_count":1,
        "eligible_signals":[{
            "symbol":"AAPL",
            "side":"BUY",
            "quantity":"1",
            "strategy_id":"TEST",
            "source_confidence":conf,
            "source_reward_risk":rr,
        }],
        "signal_capture_allowed":True,
        "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
        "all_fresh":True,
        "evidence_only":True,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }


class TestCorrectedV2117(unittest.TestCase):
    def test_ready_requires_075_and_rr_10(self):
        r=qualify_evidence_row_v2_1_17(
            row("0.80","1.20")
        )
        self.assertTrue(r["ready"])
        self.assertEqual(
            r["canonical_min_confidence"],
            "0.75",
        )
        self.assertEqual(
            r["canonical_min_reward_risk"],
            "1.0",
        )

    def test_065_is_not_ready(self):
        self.assertFalse(
            qualify_evidence_row_v2_1_17(
                row("0.65","1.20")
            )["ready"]
        )

    def test_rr_08_is_not_ready(self):
        self.assertFalse(
            qualify_evidence_row_v2_1_17(
                row("0.80","0.80")
            )["ready"]
        )

    def test_status_semantics(self):
        s=build_v2_1_17_status()
        self.assertEqual(
            s["generic_etrade_bridge_min_confidence"],
            "0.60",
        )
        self.assertFalse(
            s["generic_etrade_is_canonical_paper"]
        )
        self.assertEqual(
            s["canonical_confidence_floor"],
            "0.75",
        )
        self.assertEqual(
            s["canonical_min_reward_risk"],
            "1.0",
        )

if __name__=="__main__":
    unittest.main()
