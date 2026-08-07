import json
import tempfile
import unittest
from pathlib import Path

from data_integrity_v61_v65 import DataIntegrityRecoveryPack


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        ledger = (
            root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )
        ledger.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "trade_id": "T1",
                "symbol": "AAPL",
                "entry_time": "2026-08-01T14:00:00+00:00",
                "exit_time": "2026-08-01T15:00:00+00:00",
                "realized_pl": 10.0,
            },
            {
                "trade_id": "T2",
                "symbol": "SPY",
                "entry_time": "2026-08-02T14:00:00+00:00",
                "exit_time": "2026-08-02T15:00:00+00:00",
                "realized_pl": -5.0,
            },
        ]
        with ledger.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_integrity_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = DataIntegrityRecoveryPack(root).v61_integrity_check()
            self.assertEqual(r["status"], "PASS")

    def test_duplicate_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            ledger = (
                root
                / "runtime/closed_trade_outcome_v41_v45/"
                  "closed_trade_outcomes.jsonl"
            )
            with ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "trade_id": "T1",
                    "symbol": "AAPL",
                    "entry_time": "2026-08-03T14:00:00+00:00",
                    "exit_time": "2026-08-03T15:00:00+00:00",
                    "realized_pl": 1.0,
                }) + "\n")
            r = DataIntegrityRecoveryPack(root).v61_integrity_check()
            self.assertIn("T1", r["duplicate_trade_ids"])

    def test_incremental_first_run_detects_all(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = DataIntegrityRecoveryPack(root).v62_incremental_processor()
            self.assertEqual(r["new_trade_count"], 2)

    def test_incremental_second_run_detects_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            svc = DataIntegrityRecoveryPack(root)
            svc.v62_incremental_processor()
            r = svc.v62_incremental_processor()
            self.assertEqual(r["new_trade_count"], 0)

    def test_recovery_checkpoint_no_restore(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = DataIntegrityRecoveryPack(root).v64_recovery_checkpoint()
            self.assertFalse(r["automatic_restore_performed"])

    def test_missing_data_still_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = DataIntegrityRecoveryPack(root).run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            DataIntegrityRecoveryPack(root).run()
            rt = root / "runtime/data_integrity_v61_v65"
            self.assertTrue(
                (rt / "latest_data_integrity_report.json").exists()
            )
            self.assertTrue(
                (rt / "daily_data_health_summary.json").exists()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
