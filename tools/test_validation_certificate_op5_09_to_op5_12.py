import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.validation_certificate import (
    ValidationCertificateFoundation,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(self, complete=True, issue=False):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        self.write(root/"policy.json", {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "hash_algorithm": "SHA-256",
        })
        self.write(root/"summary.json", {
            "pilot_id": "pilot-1",
            "session_id": "session-1",
            "validation_days": 5 if complete else 0,
            "healthy_days": 5 if complete else 0,
            "unhealthy_days": 0,
            "consecutive_healthy_days": 5 if complete else 0,
            "validation_complete": complete,
        })
        self.write(root/"gate.json", {
            "validation_gate_clear": complete,
        })
        self.write(root/"analytics.json", {
            "state": (
                "VALIDATION_ANALYTICS_COMPLETE"
                if complete else "WAIT_VALIDATION_DATA"
            ),
            "average_return_pct": 1.2,
            "maximum_drawdown_pct": 0.5,
            "healthy_rate_pct": 100,
        })

        result = ValidationCertificateFoundation().run(
            policy_path=root/"policy.json",
            validation_summary_path=root/"summary.json",
            validation_gate_path=root/"gate.json",
            analytics_result_path=root/"analytics.json",
            certificate_path=root/"certificate.json",
            seal_path=root/"certificate.sha256",
            manifest_path=root/"manifest.json",
            verify_path=root/"verify.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            issue_certificate=issue,
        )
        return result, root

    def test_wait_before_validation_complete(self):
        result, _ = self.run_case(complete=False, issue=True)
        self.assertEqual(result["state"], "WAIT_VALIDATION_COMPLETE")
        self.assertFalse(result["certificate_written"])

    def test_ready_without_issue(self):
        result, _ = self.run_case(complete=True, issue=False)
        self.assertEqual(result["state"], "VALIDATION_CERTIFICATE_READY")

    def test_certificate_creation(self):
        result, root = self.run_case(complete=True, issue=True)
        self.assertTrue(result["certificate_written"])
        self.assertTrue((root/"certificate.json").exists())

    def test_manifest_and_sha256(self):
        result, root = self.run_case(complete=True, issue=True)
        self.assertTrue(result["manifest_written"])
        self.assertTrue(result["seal_written"])
        self.assertEqual(len(result["certificate_sha256"]), 64)

    def test_certificate_verify(self):
        result, _ = self.run_case(complete=True, issue=True)
        self.assertTrue(result["certificate_verified"])
        self.assertEqual(
            result["state"], "VALIDATION_CERTIFICATE_VERIFIED"
        )

    def test_read_only_contract(self):
        result, _ = self.run_case(complete=False)
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertFalse(result["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main()
