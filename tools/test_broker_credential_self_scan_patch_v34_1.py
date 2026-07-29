import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "broker_credential_self_scan_patch_v34_1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "broker_credential_self_scan_patch_v34_1",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class BrokerCredentialSelfScanPatchV341Tests(unittest.TestCase):
    def test_test_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "test_secret_fixture.py").write_text(
                "API_KEY=ABCDEFGHIJKLMNOP\n",
                encoding="utf-8",
            )
            result = MOD.scan_for_plaintext_secrets(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["finding_count"], 0)
            self.assertGreater(
                result["skipped_by_reason"].get(
                    "excluded_file_pattern", 0
                ),
                0,
            )

    def test_env_file_is_still_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "API_KEY=ABCDEFGHIJKLMNOP\n",
                encoding="utf-8",
            )
            result = MOD.scan_for_plaintext_secrets(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["findings"][0]["path"], ".env")

    def test_release_directory_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "release" / "audit"
            target.mkdir(parents=True)
            (target / "report.json").write_text(
                '{"api_key":"ABCDEFGHIJKLMNOP"}',
                encoding="utf-8",
            )
            result = MOD.scan_for_plaintext_secrets(root)
            self.assertEqual(result["status"], "PASS")

    def test_real_source_secret_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "api_secret = 'ABCDEFGHIJKLMNOP'\n",
                encoding="utf-8",
            )
            result = MOD.scan_for_plaintext_secrets(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["findings"][0]["path"], "app.py")

    def test_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "Use environment variables for broker credentials.\n",
                encoding="utf-8",
            )
            result = MOD.scan_for_plaintext_secrets(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["finding_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
