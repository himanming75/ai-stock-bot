from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.manual_sandbox_review_packet_builder_v2_1_18 import (
    ManualSandboxReviewPacketBuilderV2118,
)


def corrected_ready(key="ev1"):
    return {
        "evidence_key":key,
        "source_observed_at_utc":"2026-08-10T14:01:00+00:00",
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "ready":True,
        "reasons":[],
        "eligible_signal_count":1,
        "signals":[{
            "symbol":"AAPL",
            "side":"BUY",
            "quantity":"1",
            "strategy_id":"TEST",
            "source_confidence":"0.80",
            "source_reward_risk":"1.20",
        }],
        "generic_etrade_bridge_min_confidence":"0.60",
        "canonical_min_confidence":"0.75",
        "canonical_min_reward_risk":"1.0",
        "canonical_paper_gate_semantics":"CORRECTED_V2_1_19_1",
        "manual_review_required":True,
        "automatic_sandbox_execution_allowed":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }


def write_rows(root,rows):
    p=Path(root)/"runtime"/"sandbox_readiness_gate_v2_1_17"
    p.mkdir(parents=True,exist_ok=True)
    with (p/"qualification_ledger.jsonl").open("w",encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row)+"\n")


class TestCorrectedV2118(unittest.TestCase):
    def test_corrected_ready_builds(self):
        with tempfile.TemporaryDirectory() as td:
            write_rows(td,[corrected_ready()])
            r=ManualSandboxReviewPacketBuilderV2118(td).build()
            self.assertEqual(r["new_packets"],1)
            packet=json.loads(
                Path(r["generated_packets"][0]["json_path"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(packet["canonical_min_confidence"],"0.75")
            self.assertEqual(packet["canonical_min_reward_risk"],"1.0")

    def test_legacy_060_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            legacy=corrected_ready()
            legacy["canonical_min_confidence"]="0.60"
            legacy.pop("canonical_paper_gate_semantics")
            write_rows(td,[legacy])
            r=ManualSandboxReviewPacketBuilderV2118(td).build()
            self.assertEqual(r["new_packets"],0)
            self.assertEqual(r["legacy_or_not_ready_rows"],1)

if __name__=="__main__":
    unittest.main()
