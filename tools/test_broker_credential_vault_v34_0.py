import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("broker_credential_vault_v34_0.py")
SPEC = importlib.util.spec_from_file_location(
    "broker_credential_vault_v34_0",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class BrokerCredentialVaultV340Tests(unittest.TestCase):
    def test_missing_credentials_are_incomplete(self):
        status = MOD.inspect_credentials(MOD.BrokerName.ALPACA, {})
        self.assertFalse(status.ready)
        self.assertEqual(status.status, "INCOMPLETE")
        self.assertTrue(status.missing_required)

    def test_credentials_are_redacted(self):
        env = {
            "AI_BOT_ALPACA_API_KEY": "ABCDEFGH12345678",
            "AI_BOT_ALPACA_API_SECRET": "SECRET1234567890",
            "AI_BOT_ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
        }
        status = MOD.inspect_credentials(MOD.BrokerName.ALPACA, env)
        self.assertTrue(status.ready)
        self.assertNotIn("ABCDEFGH12345678", status.redacted.values())
        self.assertEqual(len(status.fingerprints["api_key"]), 64)

    def test_template_contains_no_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "template.json"
            MOD.generate_template(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            text = json.dumps(payload)
            self.assertIn("AI_BOT_ALPACA_API_KEY", text)
            self.assertNotIn("SECRET123", text)
            self.assertFalse(payload["enabled"])

    def test_plaintext_secret_scan_detects_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "API_KEY=ABCDEFGHIJKLMNOP\n",
                encoding="utf-8",
            )
            result = MOD.scan_for_plaintext_secrets(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["finding_count"], 1)

    def test_plaintext_secret_scan_passes_clean_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "Use environment variables for credentials.\n",
                encoding="utf-8",
            )
            result = MOD.scan_for_plaintext_secrets(root)
            self.assertEqual(result["status"], "PASS")

    def test_ibkr_validation(self):
        env = {
            "AI_BOT_IBKR_HOST": "127.0.0.1",
            "AI_BOT_IBKR_PORT": "7497",
            "AI_BOT_IBKR_CLIENT_ID": "7",
        }
        status = MOD.inspect_credentials(MOD.BrokerName.IBKR, env)
        self.assertTrue(status.ready)
        self.assertEqual(status.status, "READY_REFERENCE_ONLY")

    def test_invalid_base_url_is_rejected(self):
        env = {
            "AI_BOT_ALPACA_API_KEY": "ABCDEFGHIJKLMNOP",
            "AI_BOT_ALPACA_API_SECRET": "ABCDEFGHIJKLMNOP",
            "AI_BOT_ALPACA_BASE_URL": "http://example.com",
        }
        status = MOD.inspect_credentials(MOD.BrokerName.ALPACA, env)
        self.assertFalse(status.ready)
        self.assertEqual(status.status, "INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
