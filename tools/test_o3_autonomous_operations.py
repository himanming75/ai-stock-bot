from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from operations.audit_export import export_audit
from operations.error_stats import collect_error_statistics
from operations.health_score import calculate_health_score
from operations.latency_stats import collect_latency_statistics
from operations.timeline import build_timeline


class Tests(unittest.TestCase):
    def test_empty_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(build_timeline(Path(directory)), [])

    def test_empty_latency(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_latency_statistics(Path(directory))
        self.assertEqual(result["sample_count"], 0)

    def test_empty_error_stats(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_error_statistics(Path(directory))
        self.assertEqual(result["total_records_scanned"], 0)

    def test_audit_export_creates_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Minimum P4 policy for health/scheduler.
            policy = (
                root / "release/p4_autonomous_paper_runtime/config/"
                       "p4_runtime_policy.json"
            )
            policy.parent.mkdir(parents=True, exist_ok=True)
            policy.write_text(
                '{"cycle_interval_seconds":60,'
                '"maximum_cycles_per_session":390,'
                '"require_market_open":true,'
                '"fail_closed":true}',
                encoding="utf-8",
            )
            checkpoint = (
                root / "release/p4_autonomous_paper_runtime/actual/"
                       "runtime_checkpoint.json"
            )
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text("{}", encoding="utf-8")
            result = export_audit(root, root / "export")
            self.assertTrue(Path(result["json_path"]).exists())
            self.assertTrue(Path(result["csv_path"]).exists())

    def test_health_never_enables_live(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = (
                root / "release/p4_autonomous_paper_runtime/config/"
                       "p4_runtime_policy.json"
            )
            policy.parent.mkdir(parents=True, exist_ok=True)
            policy.write_text(
                '{"cycle_interval_seconds":60,'
                '"maximum_cycles_per_session":390,'
                '"require_market_open":true,'
                '"fail_closed":true}',
                encoding="utf-8",
            )
            checkpoint = (
                root / "release/p4_autonomous_paper_runtime/actual/"
                       "runtime_checkpoint.json"
            )
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text("{}", encoding="utf-8")
            result = calculate_health_score(root)
        self.assertIn(result["state"], {"HEALTHY", "DEGRADED"})
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
