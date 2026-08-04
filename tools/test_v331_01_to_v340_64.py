from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from observation_governance.engine import govern


def write_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class Tests(unittest.TestCase):
    def make_root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        policy = {
            "governance_enabled": True,
            "monitor_only": True,
            "paper_submission_enabled": False,
            "live_submission_enabled": False,
            "broker_write_enabled": False,
            "paper_endpoint_only": True,
            "maximum_new_orders_per_day": 0,
            "required_qualification_state": "REAL_PAPER_LONG_RUN_QUALIFIED",
            "minimum_successful_cycles": 120,
            "minimum_observation_minutes": 60,
            "minimum_success_ratio": 0.98,
            "maximum_excessive_gaps": 2,
        }
        write_json(root / "release/v331_01_to_v340_64/config/observation_governance_policy.json", policy)
        qualification = {
            "state": "REAL_PAPER_LONG_RUN_QUALIFIED",
            "status": "PASS",
            "checks": {
                "paper_submission_disabled": True,
                "live_submission_disabled": True,
                "broker_write_disabled": True,
                "zero_new_orders": True,
            },
            "statistics": {
                "successful_cycles": 120,
                "observation_minutes": 62.72,
                "success_ratio": 1.0,
                "blocked_cycles": 0,
                "error_records": 0,
            },
            "continuity": {
                "invalid_timestamp_count": 0,
                "duplicate_record_count": 0,
                "excessive_gap_count": 0,
                "maximum_gap_seconds": 31.5,
            },
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
        }
        qpath = root / "release/v321_01_to_v330_64/actual/real_paper_long_run_qualification_result.json"
        write_json(qpath, qualification)
        write_jsonl(root / "release/v321_01_to_v330_64/actual/long_run_cycle_ledger.jsonl",
                    [{"cycle_success": True, "observed_at": f"2026-08-04T18:{i:02d}:00Z"} for i in range(2)])
        write_jsonl(root / "release/v321_01_to_v330_64/actual/long_run_error_ledger.jsonl", [])
        return temp, root, qpath

    def test_qualified(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        result = govern(root, qpath, persist=False)
        self.assertEqual(result["state"], "REAL_PAPER_OBSERVATION_GOVERNANCE_QUALIFIED")

    def test_pending_qualification_blocked(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        value = json.loads(qpath.read_text())
        value["state"] = "REAL_PAPER_LONG_RUN_QUALIFICATION_PENDING"
        write_json(qpath, value)
        result = govern(root, qpath, persist=False)
        self.assertEqual(result["health"], "CRITICAL")

    def test_blocked_cycle_warning(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        value = json.loads(qpath.read_text())
        value["statistics"]["blocked_cycles"] = 1
        write_json(qpath, value)
        result = govern(root, qpath, persist=False)
        self.assertIn("BLOCKED_CYCLE_DETECTED", result["incidents"])

    def test_corrupt_ledger_critical(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        ledger = root / "release/v321_01_to_v330_64/actual/long_run_cycle_ledger.jsonl"
        ledger.write_text('{"cycle_success": true}\nnot-json\n', encoding="utf-8")
        result = govern(root, qpath, persist=False)
        self.assertEqual(result["health"], "CRITICAL")

    def test_persistence(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        govern(root, qpath, persist=True)
        self.assertTrue((root / "release/v331_01_to_v340_64/actual/governance_ledger.jsonl").exists())

    def test_zero_orders(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        result = govern(root, qpath, persist=False)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_policy_violation(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        p = root / "release/v331_01_to_v340_64/config/observation_governance_policy.json"
        value = json.loads(p.read_text())
        value["broker_write_enabled"] = True
        write_json(p, value)
        result = govern(root, qpath, persist=False)
        self.assertIn("SAFETY_POLICY_VIOLATION", result["incidents"])

    def test_deterministic_without_persist(self):
        temp, root, qpath = self.make_root()
        self.addCleanup(temp.cleanup)
        a = govern(root, qpath, persist=False)
        b = govern(root, qpath, persist=False)
        for value in (a, b):
            value.pop("observed_at", None)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
