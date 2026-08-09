from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.manual_sandbox_review_packet_builder_v2_1_18 import (
    ManualSandboxReviewPacketBuilderV2118,
)
from broker_integration_v1.manual_sandbox_review_packet_builder_status_v2_1_18 import (
    build_v2_1_18_status,
)


def ready_row(key="ev1"):
    return {
        "stage":"BROKER_INTEGRATION_V2_1_17_EVIDENCE_QUALIFICATION_SANDBOX_READINESS_GATE",
        "source_observed_at_utc":"2026-08-10T14:01:00+00:00",
        "evidence_key":key,
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "ready":True,
        "reasons":[],
        "eligible_signal_count":1,
        "signals":[{
            "symbol":"AAPL",
            "side":"BUY",
            "quantity":"1",
            "strategy_id":"TEST",
            "source_confidence":"0.65",
        }],
        "canonical_min_confidence":"0.60",
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


class TestV2118(unittest.TestCase):
    def test_missing_source_waits(self):
        with tempfile.TemporaryDirectory() as td:
            r=ManualSandboxReviewPacketBuilderV2118(td).build()
            self.assertEqual(r["status"],"WAITING_FOR_V2_1_17_QUALIFICATION")
            self.assertEqual(r["broker_orders_submitted"],0)

    def test_ready_packet_builds(self):
        with tempfile.TemporaryDirectory() as td:
            write_rows(td,[ready_row()])
            r=ManualSandboxReviewPacketBuilderV2118(td).build()
            self.assertEqual(r["ready_rows"],1)
            self.assertEqual(r["new_packets"],1)
            item=r["generated_packets"][0]
            self.assertTrue(Path(item["json_path"]).exists())
            self.assertTrue(Path(item["markdown_path"]).exists())

    def test_not_ready_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            row=ready_row()
            row["ready"]=False
            row["qualification_status"]="NOT_READY"
            write_rows(td,[row])
            r=ManualSandboxReviewPacketBuilderV2118(td).build()
            self.assertEqual(r["ready_rows"],0)
            self.assertEqual(r["new_packets"],0)

    def test_deduplication(self):
        with tempfile.TemporaryDirectory() as td:
            write_rows(td,[ready_row("same")])
            b=ManualSandboxReviewPacketBuilderV2118(td)
            first=b.build()
            second=b.build()
            self.assertEqual(first["new_packets"],1)
            self.assertEqual(second["new_packets"],0)
            self.assertEqual(second["duplicate_packets"],1)

    def test_status_locks(self):
        s=build_v2_1_18_status()
        self.assertTrue(s["manual_review_required"])
        self.assertFalse(s["manual_approval_recording_from_stage"])
        self.assertFalse(s["automatic_sandbox_execution_allowed"])
        self.assertFalse(s["etrade_oauth_from_stage"])
        self.assertFalse(s["sandbox_place_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
