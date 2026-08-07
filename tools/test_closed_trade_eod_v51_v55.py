import json
import tempfile
import unittest
from pathlib import Path

from closed_trade_eod_v51_v55 import ClosedTradeEODPipeline


class Tests(unittest.TestCase):
    def test_archive_empty_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeEODPipeline(root)
            r = svc.v54_archive_daily_snapshot()
            self.assertEqual(r["status"], "PASS")
            self.assertEqual(r["copied_count"], 0)

    def test_readiness_advisory_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeEODPipeline(root)
            r = svc.v55_readiness_summary()
            self.assertFalse(r["live_submission_enabled"])
            self.assertEqual(
                r["deployment_effect"], "ADVISORY_ONLY"
            )

    def test_missing_collector_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeEODPipeline(root)
            r = svc.v52_refresh_collector()
            self.assertEqual(r["status"], "BLOCKED")

    def test_missing_analytics_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeEODPipeline(root)
            r = svc.v53_refresh_analytics()
            self.assertEqual(r["status"], "BLOCKED")

    def test_runtime_directory_created(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeEODPipeline(root)
            self.assertTrue(svc.runtime.exists())

    def test_no_broker_write_flag_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = ClosedTradeEODPipeline(root)
            r = svc.v54_archive_daily_snapshot()
            self.assertFalse(r["broker_write_performed"])

    def test_summary_reads_existing_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = (
                root
                / "runtime/closed_trade_analytics_v46_v50/"
                  "latest_closed_trade_analytics_report.json"
            )
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({
                "v50_readiness_gate": {
                    "status": "INSUFFICIENT_SAMPLE",
                    "passed_checks": 2,
                    "total_checks": 9,
                    "blockers": ["closed_trades_at_least_20"]
                }
            }), encoding="utf-8")
            svc = ClosedTradeEODPipeline(root)
            r = svc.v55_readiness_summary()
            self.assertEqual(
                r["readiness_status"], "INSUFFICIENT_SAMPLE"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
