from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from final_offline_rc.audit import (
    CredentialLeakageAudit,
    JsonIntegrityAudit,
    SafetyInvariantAudit,
)


class Tests(unittest.TestCase):
    def test_json_integrity_detects_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "release/x/actual/result.json"
            path.parent.mkdir(parents=True)
            path.write_text('{"status":"PASS"}', encoding="utf-8")
            result = JsonIntegrityAudit().run(root)
            self.assertEqual(result["status"], "PASS")

    def test_json_integrity_detects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "release/x/actual/result.json"
            path.parent.mkdir(parents=True)
            path.write_text("{bad", encoding="utf-8")
            result = JsonIntegrityAudit().run(root)
            self.assertEqual(result["status"], "FAIL")

    def test_safety_violation_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "release/x/actual/x_result.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps({
                    "actual_broker_write_performed": True,
                    "actual_order_submission_performed": False,
                    "actual_live_orders_submitted": 0,
                }),
                encoding="utf-8",
            )
            result = SafetyInvariantAudit().run(root)
            self.assertEqual(result["status"], "FAIL")

    def test_redacted_credentials_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "x.json"
            path.write_text(
                '{"api_key":"[REDACTED]","secret_key":"[REDACTED]"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "PASS")

    def test_plaintext_credentials_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "x.json"
            path.write_text(
                '{"api_key":"plaintext-value"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
