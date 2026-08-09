from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_v2_1_17 import (
    qualify_evidence_row_v2_1_17,
    EvidenceQualificationSandboxReadinessGateV2117,
)
from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_status_v2_1_17 import (
    build_v2_1_17_status,
)


def ready_evidence(key="ev1"):
    return {
        "stage":"BROKER_INTEGRATION_V2_1_16_FRESH_ELIGIBLE_SIGNAL_EVIDENCE_CAPTURE",
        "evidence_key":key,
        "observed_at_utc":"2026-08-10T14:01:00+00:00",
        "observer_state":"OBSERVED_FRESH",
        "canonical_gate_aligned":True,
        "eligible_signal_count":1,
        "eligible_signals":[{
            "symbol":"AAPL",
            "side":"BUY",
            "quantity":"1",
            "strategy_id":"TEST",
            "source_confidence":"0.65",
        }],
        "signal_capture_allowed":True,
        "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
        "all_fresh":True,
        "evidence_only":True,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }


def write_evidence(root, rows):
    p=(
        Path(root)
        /"runtime"
        /"fresh_eligible_signal_evidence_v2_1_16"
    )
    p.mkdir(parents=True,exist_ok=True)
    with (p/"eligible_signal_evidence.jsonl").open(
        "w",encoding="utf-8"
    ) as f:
        for row in rows:
            f.write(json.dumps(row)+"\n")


class TestV2117(unittest.TestCase):
    def test_ready_evidence(self):
        r=qualify_evidence_row_v2_1_17(ready_evidence())
        self.assertTrue(r["ready"])
        self.assertEqual(
            r["qualification_status"],
            "READY_FOR_MANUAL_SANDBOX_REVIEW",
        )
        self.assertFalse(r["automatic_sandbox_execution_allowed"])

    def test_low_confidence_not_ready(self):
        row=ready_evidence()
        row["eligible_signals"][0]["source_confidence"]="0.59"
        r=qualify_evidence_row_v2_1_17(row)
        self.assertFalse(r["ready"])
        self.assertIn(
            "SIGNAL_1_CONFIDENCE_BELOW_CANONICAL",
            r["reasons"],
        )

    def test_invalid_side_not_ready(self):
        row=ready_evidence()
        row["eligible_signals"][0]["side"]="HOLD"
        r=qualify_evidence_row_v2_1_17(row)
        self.assertFalse(r["ready"])
        self.assertIn("SIGNAL_1_INVALID_SIDE",r["reasons"])

    def test_missing_evidence_waits(self):
        with tempfile.TemporaryDirectory() as td:
            r=EvidenceQualificationSandboxReadinessGateV2117(td).evaluate()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_1_16_EVIDENCE",
            )
            self.assertEqual(r["broker_orders_submitted"],0)

    def test_ledger_and_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            write_evidence(td,[ready_evidence("same")])
            g=EvidenceQualificationSandboxReadinessGateV2117(td)
            a=g.evaluate()
            b=g.evaluate()
            self.assertEqual(a["ready_rows"],1)
            self.assertEqual(a["new_qualification_rows"],1)
            self.assertEqual(b["new_qualification_rows"],0)
            self.assertEqual(b["duplicate_qualification_rows"],1)

    def test_status_locks(self):
        s=build_v2_1_17_status()
        self.assertTrue(s["manual_sandbox_review_only"])
        self.assertFalse(s["automatic_sandbox_execution_allowed"])
        self.assertFalse(s["etrade_oauth_from_stage"])
        self.assertFalse(s["sandbox_place_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
