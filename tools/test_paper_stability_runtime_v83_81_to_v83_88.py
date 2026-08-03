from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.paper_stability_runtime_v83_81_88 import (
    run_paper_stability_runtime_readiness,
)


class PaperStabilityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.json"
        self.ledger = self.root / "ledger.jsonl"
        self.policy = self.root / "policy.json"
        self.cert = self.root / "cert.json"
        self.runtime = self.root / "runtime.json"
        self.audit = self.root / "audit.json"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        self.policy.write_text(json.dumps({
            "paper_only": True,
            "minimum_validation_days": 3,
            "minimum_stability_score": 100,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "continuous_loop_enabled": False,
            "windows_task_enabled": False,
            "automatic_broker_execution_enabled": False,
        }), encoding="utf-8")

    def write_case(self, days=1, unsafe=False, duplicate=False):
        dates = ["2026-08-03", "2026-08-04", "2026-08-05"][:days]
        rows = []
        for day in dates:
            rows.append({
                "validation_date": day,
                "paper_only": True,
                "broker_write_enabled": unsafe,
                "order_submission_enabled": False,
                "live_trading_enabled": False,
                "external_network_enabled": False,
                "actual_paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "network_requests_executed": 0,
                "write_requests_executed": 0,
            })
        if duplicate and rows:
            rows.append(dict(rows[0]))
        self.ledger.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        self.source.write_text(json.dumps({
            "stage_range": "V83.77-V83.80",
            "status": "PASS",
            "completed_days": days,
            "requirement_met": days >= 3,
        }), encoding="utf-8")

    def execute_case(self):
        return run_paper_stability_runtime_readiness(
            multi_day_result_path=self.source,
            daily_ledger_path=self.ledger,
            policy_path=self.policy,
            certificate_path=self.cert,
            runtime_policy_path=self.runtime,
            audit_path=self.audit,
            dashboard_path=self.dashboard,
            result_path=self.result,
            observed_at_override="2026-08-05T20:00:00+00:00",
        )

    def test_one_day_pending(self):
        self.write_case(1)
        result = self.execute_case()
        self.assertEqual(result["state"], "PAPER_STABILITY_CERTIFICATION_PENDING")
        self.assertEqual(result["remaining_days"], 2)
        self.assertEqual(result["status"], "PASS")

    def test_three_days_certified(self):
        self.write_case(3)
        result = self.execute_case()
        self.assertEqual(result["state"], "EXTENDED_PAPER_RUNTIME_READY")
        self.assertTrue(result["certificate_valid"])
        self.assertTrue(self.cert.exists())

    def test_duplicate_ledger_blocks(self):
        self.write_case(3, duplicate=True)
        result = self.execute_case()
        self.assertEqual(result["status"], "BLOCKED")

    def test_unsafe_ledger_blocks(self):
        self.write_case(3, unsafe=True)
        result = self.execute_case()
        self.assertEqual(result["status"], "BLOCKED")

    def test_missing_source_blocks(self):
        self.write_case(1)
        self.source.unlink()
        result = self.execute_case()
        self.assertEqual(result["status"], "BLOCKED")

    def test_certificate_digest(self):
        self.write_case(3)
        self.execute_case()
        value = json.loads(self.cert.read_text(encoding="utf-8"))
        self.assertEqual(len(value["certificate_sha256"]), 64)

    def test_runtime_policy_stays_safe(self):
        self.write_case(3)
        self.execute_case()
        value = json.loads(self.runtime.read_text(encoding="utf-8"))
        self.assertFalse(value["broker_write_enabled"])
        self.assertFalse(value["continuous_loop_enabled"])

    def test_next_phase_after_certification(self):
        self.write_case(3)
        result = self.execute_case()
        self.assertEqual(result["next_phase"], "V83_89_PAPER_PERFORMANCE_EVALUATION")


if __name__ == "__main__":
    unittest.main()
