import json
import tempfile
import unittest
from pathlib import Path

from integrated_validation_v81_v85 import IntegratedValidationDailyReview


class Tests(unittest.TestCase):
    def test_cross_module_missing_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = IntegratedValidationDailyReview(root)
            r = svc.v81_cross_module_data_flow_check()
            self.assertGreater(len(r["missing_modules"]), 0)

    def test_propagation_empty_is_consistent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = IntegratedValidationDailyReview(root)
            r = svc.v82_closed_trade_propagation_check()
            self.assertTrue(r["consistent"])

    def test_daily_snapshot_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = IntegratedValidationDailyReview(root)
            r = svc.v83_daily_validation_snapshot()
            self.assertFalse(r["broker_write_performed"])

    def test_multiday_collecting_history(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = IntegratedValidationDailyReview(root)
            r = svc.v84_multiday_collection_readiness()
            self.assertEqual(r["status"], "COLLECTING_HISTORY")

    def test_summary_advisory_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = IntegratedValidationDailyReview(root)
            r = svc.v85_integrated_validation_summary()
            self.assertEqual(r["deployment_effect"], "ADVISORY_ONLY")
            self.assertFalse(r["live_submission_enabled"])

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = IntegratedValidationDailyReview(root)
            r = svc.run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            svc = IntegratedValidationDailyReview(root)
            svc.run()
            rt = root / "runtime/integrated_validation_v81_v85"
            self.assertTrue(
                (rt / "latest_integrated_validation_report.json").exists()
            )
            self.assertTrue(
                (rt / "daily_validation_snapshot.json").exists()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
