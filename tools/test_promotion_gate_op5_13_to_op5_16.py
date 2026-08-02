import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.promotion_gate import PaperPilotPromotionGate


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        policy = {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "minimum_validation_days": 5,
            "minimum_healthy_rate_pct": 80,
            "minimum_average_return_pct": 0,
            "maximum_drawdown_pct": 5,
        }
        summary = {
            "validation_complete": True,
            "validation_days": 5,
        }
        gate = {"validation_gate_clear": True}
        analytics = {
            "state": "VALIDATION_ANALYTICS_COMPLETE",
            "healthy_rate_pct": 100,
            "average_return_pct": 1.0,
            "maximum_drawdown_pct": 1.0,
        }
        certificate = {
            "certificate_verified": True,
            "certificate_id": "VAL-1",
            "certificate_sha256": "a" * 64,
        }
        risk = {
            "state": "PAPER_RISK_HEALTHY",
            "emergency_stop_required": False,
        }
        return policy, summary, gate, analytics, certificate, risk

    def run_case(self, values):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["policy", "summary", "gate", "analytics", "certificate", "risk"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            self.write(paths[name], value)

        result = PaperPilotPromotionGate().run(
            policy_path=paths["policy"],
            validation_summary_path=paths["summary"],
            validation_gate_path=paths["gate"],
            analytics_result_path=paths["analytics"],
            certificate_result_path=paths["certificate"],
            risk_result_path=paths["risk"],
            promotion_manifest_path=root/"manifest.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_promotion_ready(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["state"], "PROMOTION_READY")
        self.assertTrue(result["promotion_ready"])

    def test_validation_required(self):
        values = list(self.data())
        values[1] = {"validation_complete": False, "validation_days": 0}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_VALIDATION_COMPLETE")

    def test_certificate_required(self):
        values = list(self.data())
        values[4] = {"certificate_verified": False}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_CERTIFICATE_VERIFICATION")

    def test_performance_gate(self):
        values = list(self.data())
        values[3] = dict(values[3])
        values[3]["maximum_drawdown_pct"] = 10
        result, _ = self.run_case(tuple(values))
        self.assertIn(
            "MAXIMUM_DRAWDOWN_EXCEEDED",
            result["promotion_reasons"],
        )

    def test_risk_gate(self):
        values = list(self.data())
        values[5] = {
            "state": "EMERGENCY_STOP_REQUIRED",
            "emergency_stop_required": True,
        }
        result, _ = self.run_case(tuple(values))
        self.assertIn(
            "EMERGENCY_STOP_REQUIRED",
            result["promotion_reasons"],
        )

    def test_read_only_contract(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertFalse(result["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main()
