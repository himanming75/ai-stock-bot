from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from final_offline_rc.audit import CredentialLeakageAudit


class Tests(unittest.TestCase):
    def test_tools_test_file_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "tools/test_example.py"
            path.parent.mkdir(parents=True)
            path.write_text(
                '{"api_key":"PK7H29JQ81Y5C0X9M4L2"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["excluded_example_files"], 1)

    def test_release_docs_markdown_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "release/v1/docs/EXAMPLE.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                'APCA_API_KEY_ID="PK7H29JQ81Y5C0X9M4L2"',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "PASS")

    def test_staging_test_copy_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "release/v1/output/staging/tools/test_copy.py"
            path.parent.mkdir(parents=True)
            path.write_text(
                '{"secret_key":"aB7xQ2mN9pL4sT8vW3yK6zR1cF5h"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "PASS")

    def test_runtime_code_real_key_remains_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "runtime/config.py"
            path.parent.mkdir(parents=True)
            path.write_text(
                '{"api_key":"PK7H29JQ81Y5C0X9M4L2"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "FAIL")

    def test_plaintext_regression_fixture_outside_excluded_path_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "unsafe.json"
            path.write_text(
                '{"api_key":"plaintext-value"}',
                encoding="utf-8",
            )
            result = CredentialLeakageAudit().run(root)
            self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
