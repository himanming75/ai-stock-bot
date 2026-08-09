from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.fresh_eligible_signal_evidence_capture_v2_1_16 import (
    FreshEligibleSignalEvidenceCaptureV2116,
)
from broker_integration_v1.fresh_eligible_signal_evidence_capture_status_v2_1_16 import (
    build_v2_1_16_status,
)


def write_rows(root,rows):
    p=(
        Path(root)
        /"runtime"
        /"freshness_guarded_persistent_observer_v2_1_15"
    )
    p.mkdir(parents=True,exist_ok=True)
    with (p/"observation_ledger.jsonl").open(
        "w",encoding="utf-8"
    ) as f:
        for row in rows:
            f.write(json.dumps(row)+"\n")


def eligible_row(fp="abc"):
    return {
        "stage":"BROKER_INTEGRATION_V2_1_15_FRESHNESS_GUARDED_PERSISTENT_OBSERVER",
        "observed_at_utc":"2026-08-10T14:01:00+00:00",
        "iteration":1,
        "observer_state":"OBSERVED_FRESH",
        "snapshot_fingerprint":fp,
        "eligible_signal_captured":True,
        "session_freshness_gate":{
            "status":"PASS_REGULAR_WINDOW_FRESH_BARS"
        },
        "snapshot":{
            "canonical_gate_aligned":True,
            "eligible_signal_count":1,
            "eligible_signals":[{
                "symbol":"AAPL",
                "side":"BUY",
                "quantity":"1",
                "strategy_id":"TEST",
                "source_confidence":"0.75",
            }],
            "signal_capture_allowed":True,
            "market_data_fetch_skipped":False,
            "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
            "all_fresh":True,
        },
    }


class TestV2116(unittest.TestCase):
    def test_missing_source_waits(self):
        with tempfile.TemporaryDirectory() as td:
            r=FreshEligibleSignalEvidenceCaptureV2116(td).capture()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_1_15_OBSERVATION_LEDGER",
            )
            self.assertEqual(r["broker_orders_submitted"],0)

    def test_captures_only_fresh_eligible(self):
        with tempfile.TemporaryDirectory() as td:
            rows=[
                eligible_row("one"),
                {
                    "observer_state":"WAITING_SESSION",
                    "snapshot_fingerprint":"two",
                    "eligible_signal_captured":False,
                    "snapshot":{"eligible_signal_count":0},
                },
            ]
            write_rows(td,rows)
            r=FreshEligibleSignalEvidenceCaptureV2116(td).capture()
            self.assertEqual(r["eligible_rows_found"],1)
            self.assertEqual(r["new_evidence_rows"],1)
            self.assertTrue(Path(r["evidence_ledger"]).exists())

    def test_deduplication(self):
        with tempfile.TemporaryDirectory() as td:
            write_rows(td,[eligible_row("same")])
            c=FreshEligibleSignalEvidenceCaptureV2116(td)
            first=c.capture()
            second=c.capture()
            self.assertEqual(first["new_evidence_rows"],1)
            self.assertEqual(second["new_evidence_rows"],0)
            self.assertEqual(second["duplicate_evidence_rows"],1)

    def test_status_locks(self):
        s=build_v2_1_16_status()
        self.assertTrue(s["fresh_only_filter"])
        self.assertTrue(s["eligible_only_filter"])
        self.assertTrue(s["fingerprint_deduplication"])
        self.assertFalse(s["market_data_fetch_from_stage"])
        self.assertFalse(s["etrade_oauth_from_stage"])
        self.assertFalse(s["sandbox_place_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
