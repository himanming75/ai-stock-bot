from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from final_offline_rc.audit import CredentialLeakageAudit


class Tests(unittest.TestCase):
    def test_fixture_placeholder_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.json").write_text(
                '{"api_key":"raw-key-value","secret_key":"fixture-secret"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "PASS")
            self.assertGreaterEqual(result["ignored_placeholder_count"], 2)

    def test_redacted_values_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.json").write_text(
                '{"api_key":"[REDACTED]","secret_key":"[REDACTED]"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "PASS")

    def test_plaintext_value_remains_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "unsafe.json").write_text(
                '{"api_key":"plaintext-value"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["finding_count"], 1)

    def test_realistic_api_key_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "unsafe.json").write_text(
                '{"api_key":"PK7H29JQ81Y5C0X9M4L2"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "FAIL")

    def test_realistic_secret_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "unsafe.json").write_text(
                '{"secret_key":"aB7xQ2mN9pL4sT8vW3yK6zR1cF5h"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
