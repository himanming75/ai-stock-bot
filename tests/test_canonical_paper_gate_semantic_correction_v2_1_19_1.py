from pathlib import Path
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.canonical_paper_gate_semantics_v2_1_19_1 import (
    GENERIC_ETRADE_BRIDGE_MIN_CONFIDENCE,
    CANONICAL_PAPER_MIN_CONFIDENCE,
    CANONICAL_PAPER_MIN_REWARD_RISK,
    semantic_gate_contract_v2_1_19_1,
    qualify_canonical_paper_metrics,
)
from broker_integration_v1.etrade_ai_signal_decision_v2_1_5 import (
    SignalDecisionPolicy,
)
from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_v2_1_17 import (
    qualify_evidence_row_v2_1_17,
)
from broker_integration_v1.manual_sandbox_review_packet_builder_v2_1_18 import (
    ManualSandboxReviewPacketBuilderV2118,
)
from broker_integration_v1.manual_approval_record_expiration_guard_v2_1_19 import (
    ManualApprovalRecordExpirationGuardV2119,
    APPROVAL_PHRASE,
)


def evidence(conf="0.80",rr="1.20",key="ev"):
    signal={
        "symbol":"AAPL",
        "side":"BUY",
        "quantity":"1",
        "strategy_id":"AUDIT",
        "source_confidence":conf,
    }
    if rr is not None:
        signal["source_reward_risk"]=rr
    return {
        "stage":"V2.1.16",
        "evidence_key":key,
        "observed_at_utc":"2026-08-10T14:01:00+00:00",
        "observer_state":"OBSERVED_FRESH",
        "canonical_gate_aligned":True,
        "eligible_signal_count":1,
        "eligible_signals":[signal],
        "signal_capture_allowed":True,
        "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
        "all_fresh":True,
        "evidence_only":True,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }


class TestSemanticCorrectionV21191(unittest.TestCase):
    def test_generic_gate_remains_060(self):
        p=SignalDecisionPolicy()
        self.assertEqual(
            p.minimum_confidence,
            GENERIC_ETRADE_BRIDGE_MIN_CONFIDENCE,
        )
        self.assertEqual(str(p.minimum_confidence),"0.60")

    def test_canonical_gate_is_distinct(self):
        self.assertEqual(
            str(CANONICAL_PAPER_MIN_CONFIDENCE),
            "0.75",
        )
        self.assertEqual(
            str(CANONICAL_PAPER_MIN_REWARD_RISK),
            "1.0",
        )
        c=semantic_gate_contract_v2_1_19_1()
        self.assertFalse(c["semantic_equivalence"])

    def test_065_rr_12_not_canonical(self):
        r=qualify_canonical_paper_metrics(
            "0.65","1.20"
        )
        self.assertFalse(r["ready"])
        self.assertIn(
            "CONFIDENCE_BELOW_CANONICAL_PAPER",
            r["reasons"],
        )

    def test_080_rr_08_not_canonical(self):
        r=qualify_canonical_paper_metrics(
            "0.80","0.80"
        )
        self.assertFalse(r["ready"])
        self.assertIn(
            "REWARD_RISK_BELOW_CANONICAL_PAPER",
            r["reasons"],
        )

    def test_080_rr_12_canonical(self):
        r=qualify_canonical_paper_metrics(
            "0.80","1.20"
        )
        self.assertTrue(r["ready"])

    def test_missing_rr_is_blocked(self):
        r=qualify_evidence_row_v2_1_17(
            evidence(rr=None)
        )
        self.assertFalse(r["ready"])
        self.assertIn(
            "SIGNAL_1_CANONICAL_REWARD_RISK_MISSING",
            r["reasons"],
        )

    def test_legacy_060_ready_row_cannot_build_packet(self):
        with tempfile.TemporaryDirectory() as td:
            p=(
                Path(td)
                /"runtime"
                /"sandbox_readiness_gate_v2_1_17"
            )
            p.mkdir(parents=True,exist_ok=True)
            legacy={
                "evidence_key":"legacy",
                "qualification_status":
                    "READY_FOR_MANUAL_SANDBOX_REVIEW",
                "ready":True,
                "manual_review_required":True,
                "automatic_sandbox_execution_allowed":False,
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
                "canonical_min_confidence":"0.60",
                "signals":[],
            }
            (p/"qualification_ledger.jsonl").write_text(
                json.dumps(legacy)+"\n",
                encoding="utf-8",
            )
            r=ManualSandboxReviewPacketBuilderV2118(
                td
            ).build()
            self.assertEqual(r["ready_rows"],0)
            self.assertEqual(r["new_packets"],0)

    def test_legacy_packet_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as td:
            p=(
                Path(td)
                /"runtime"
                /"manual_sandbox_review_packets_v2_1_18"
            )
            p.mkdir(parents=True,exist_ok=True)
            packet={
                "packet_status":"AWAITING_MANUAL_REVIEW",
                "evidence_key":"legacy",
                "qualification_status":
                    "READY_FOR_MANUAL_SANDBOX_REVIEW",
                "canonical_min_confidence":"0.60",
                "eligible_signal_count":1,
                "signals":[{
                    "symbol":"AAPL",
                    "side":"BUY",
                    "quantity":"1",
                    "strategy_id":"LEGACY",
                    "source_confidence":"0.65",
                }],
                "manual_review_required":True,
                "manual_approval_recorded":False,
                "automatic_sandbox_execution_allowed":False,
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }
            (
                p/"review_packet_legacy.json"
            ).write_text(
                json.dumps(packet),
                encoding="utf-8",
            )
            g=ManualApprovalRecordExpirationGuardV2119(
                td,
                now_fn=lambda:datetime(
                    2026,8,10,14,10,
                    tzinfo=timezone.utc,
                ),
            )
            r=g.approve(
                "legacy",
                APPROVAL_PHRASE,
            )
            self.assertEqual(
                r["status"],
                "NOT_APPROVED_PACKET_VALIDATION_FAILED",
            )
            self.assertIn(
                "CANONICAL_CONFIDENCE_SEMANTICS_NOT_CORRECTED",
                r["reasons"],
            )

if __name__=="__main__":
    unittest.main()
