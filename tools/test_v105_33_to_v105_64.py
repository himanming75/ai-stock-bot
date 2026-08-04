import tempfile
import unittest
from pathlib import Path

from final_release.readiness import evaluate_readiness
from final_release.certificate import build_certificate
from final_release.manifest import build_manifest
from final_release.integrity import verify_inventory
from final_release.acceptance import acceptance_test
from final_release.rollback import build_rollback_manifest
from final_release.engine import evaluate

def integration_ready():
    return {
        "state": "FINAL_SYSTEM_INTEGRATION_READY",
        "status": "PASS",
        "final_release_eligible": True,
        "integration_id": "integration",
        "readiness": {
            "readiness_score": 100.0,
            "ready_module_count": 17,
            "module_count": 17,
        },
        "pipeline": {
            "passed": True,
            "ready_steps": 17,
            "total_steps": 17,
        },
        "safety": {"passed": True},
        "actual_orders_submitted": 0,
        "execution_authorized": False,
        "paper_only": True,
    }

class Tests(unittest.TestCase):
    def test_readiness(self):
        self.assertTrue(
            evaluate_readiness(
                integration_ready(),
                {"minimum_readiness_score": 95},
            )["passed"]
        )

    def test_certificate(self):
        ready = evaluate_readiness(integration_ready(), {})
        value = build_certificate(
            integration_ready(),
            ready,
            {
                "release_version": "V105 FINAL",
                "release_name": "AI Stock Bot",
                "base_commit": "abc",
            },
        )
        self.assertEqual(len(value["certificate_sha256"]), 64)

    def test_manifest(self):
        ready = evaluate_readiness(integration_ready(), {})
        cert = build_certificate(
            integration_ready(),
            ready,
            {
                "release_version": "V105 FINAL",
                "release_name": "AI Stock Bot",
                "base_commit": "abc",
            },
        )
        value = build_manifest(
            cert,
            {"file_count": 1, "total_size_bytes": 10},
            {"base_commit": "abc", "branch": "main"},
        )
        self.assertEqual(value["module_count"], 18)

    def test_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "a.txt"
            file.write_text("a", encoding="utf-8")
            import hashlib
            expected = hashlib.sha256(b"a").hexdigest()
            value = verify_inventory(
                root,
                {
                    "file_count": 1,
                    "files": [{"path": "a.txt", "sha256": expected}],
                },
            )
            self.assertTrue(value["passed"])

    def test_acceptance(self):
        value = acceptance_test(
            {"passed": True},
            {"passed": True},
            {
                "certificate_sha256": "a" * 64,
                "release_id": "r",
                "paper_trading_ready": True,
                "live_trading_enabled": False,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "manual_approval_required": True,
                "actual_orders_submitted": 0,
            },
            {
                "manifest_sha256": "b" * 64,
                "release_id": "r",
            },
        )
        self.assertTrue(value["passed"])

    def test_rollback(self):
        value = build_rollback_manifest(
            {"release_id": "r", "release_version": "V105"},
            {"base_commit": "abc", "branch": "main"},
        )
        self.assertEqual(value["rollback_target_commit"], "abc")

    def test_missing_source_review(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp))
            self.assertFalse(result["project_complete"])

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(evaluate(Path(temp))["actual_orders_submitted"], 0)

    def test_live_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(evaluate(Path(temp))["live_trading_ready"])

if __name__ == "__main__":
    unittest.main()
