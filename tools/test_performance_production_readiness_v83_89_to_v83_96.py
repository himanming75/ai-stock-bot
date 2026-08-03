from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.performance_production_readiness_v83_89_96 import (
    run_performance_production_readiness,
)


class PerformanceProductionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.stability = self.root / "stability.json"
        self.snapshot = self.root / "snapshot.json"
        self.policy = self.root / "policy.json"
        self.report = self.root / "report.json"
        self.perf_cert = self.root / "perf_cert.json"
        self.risk = self.root / "risk.json"
        self.ready_cert = self.root / "ready_cert.json"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        self.policy.write_text(json.dumps({
            "paper_only": True,
            "minimum_trade_count": 5,
            "minimum_net_profit": 0,
            "maximum_drawdown_pct": 20,
            "minimum_profit_factor": 1.0,
            "maximum_daily_loss_pct": 5,
            "maximum_order_rejections": 0,
            "minimum_performance_score": 100,
            "maximum_position_pct": 10,
            "maximum_portfolio_exposure_pct": 50,
            "maximum_orders_per_day": 5,
            "kill_switch_required": True,
            "emergency_stop_required": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "continuous_loop_enabled": False,
            "windows_task_enabled": False,
            "automatic_broker_execution_enabled": False,
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write_stability(self, ready=True):
        self.stability.write_text(json.dumps({
            "status": "PASS",
            "state": (
                "EXTENDED_PAPER_RUNTIME_READY"
                if ready
                else "PAPER_STABILITY_CERTIFICATION_PENDING"
            ),
            "certificate_valid": ready,
        }), encoding="utf-8")

    def write_snapshot(self, passed=True):
        value = {
            "performance_snapshot_ready": True,
            "total_trades": 10,
            "winning_trades": 6,
            "losing_trades": 4,
            "gross_profit": 200,
            "gross_loss": 100,
            "net_profit": 100,
            "max_drawdown_pct": 10,
            "max_daily_loss_pct": 2,
            "order_rejection_count": 0,
            "duplicate_order_count": 0,
        }
        if not passed:
            value["max_drawdown_pct"] = 50
        self.snapshot.write_text(json.dumps(value), encoding="utf-8")

    def execute(self):
        return run_performance_production_readiness(
            stability_result_path=self.stability,
            performance_snapshot_path=self.snapshot,
            policy_path=self.policy,
            performance_report_path=self.report,
            performance_certificate_path=self.perf_cert,
            risk_gate_path=self.risk,
            readiness_certificate_path=self.ready_cert,
            dashboard_path=self.dashboard,
            result_path=self.result,
            observed_at_override="2026-08-06T20:00:00+00:00",
        )

    def test_pending_without_stability(self):
        self.write_stability(False)
        self.write_snapshot(True)
        result = self.execute()
        self.assertEqual(result["state"], "PRODUCTION_READINESS_PENDING")

    def test_pending_without_snapshot(self):
        self.write_stability(True)
        result = self.execute()
        self.assertEqual(result["state"], "PRODUCTION_READINESS_PENDING")

    def test_approved_with_good_metrics(self):
        self.write_stability(True)
        self.write_snapshot(True)
        result = self.execute()
        self.assertEqual(result["state"], "PRODUCTION_READINESS_APPROVED")
        self.assertTrue(result["readiness_certificate_valid"])

    def test_bad_drawdown_stays_pending(self):
        self.write_stability(True)
        self.write_snapshot(False)
        result = self.execute()
        self.assertFalse(result["performance_passed"])
        self.assertEqual(result["state"], "PRODUCTION_READINESS_PENDING")

    def test_profit_factor(self):
        self.write_stability(True)
        self.write_snapshot(True)
        result = self.execute()
        self.assertEqual(result["metrics"]["profit_factor"], 2.0)

    def test_unsafe_policy_blocks(self):
        value = json.loads(self.policy.read_text(encoding="utf-8"))
        value["broker_write_enabled"] = True
        self.policy.write_text(json.dumps(value), encoding="utf-8")
        self.write_stability(True)
        self.write_snapshot(True)
        result = self.execute()
        self.assertEqual(result["status"], "BLOCKED")

    def test_risk_gate_safe_defaults(self):
        self.write_stability(False)
        result = self.execute()
        self.assertTrue(result["risk_gate_passed"])
        self.assertFalse(result["broker_write_enabled"])

    def test_next_phase_after_approval(self):
        self.write_stability(True)
        self.write_snapshot(True)
        result = self.execute()
        self.assertEqual(result["next_phase"], "V83_97_PAPER_PRODUCTION_RELEASE")


if __name__ == "__main__":
    unittest.main()
