from __future__ import annotations
import unittest

from deployment.credential_vault import validate_vault_metadata


class Tests(unittest.TestCase):
    def test_securestring_provider_is_valid(self):
        result = validate_vault_metadata(
            mode="paper",
            metadata={
                "schema_version": 2,
                "encryption_provider": (
                    "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING"
                ),
                "base_url": "https://paper-api.alpaca.markets",
                "key_fingerprint": "1234567890abcdef",
                "secret_fingerprint": "abcdef1234567890",
                "encrypted_payload_file": "paper_credentials.dpapi",
            },
        )
        self.assertTrue(result["valid"])

    def test_wrong_endpoint_still_rejected(self):
        result = validate_vault_metadata(
            mode="paper",
            metadata={
                "schema_version": 2,
                "encryption_provider": (
                    "WINDOWS_DPAPI_CURRENT_USER_SECURESTRING"
                ),
                "base_url": "https://api.alpaca.markets",
                "key_fingerprint": "1234567890abcdef",
                "secret_fingerprint": "abcdef1234567890",
                "encrypted_payload_file": "paper_credentials.dpapi",
            },
        )
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
