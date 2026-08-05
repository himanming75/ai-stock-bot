from __future__ import annotations
import unittest

from deployment.credential_vault import (
    build_rotation_record,
    fingerprint,
    validate_vault_metadata,
)


class Tests(unittest.TestCase):
    def test_fingerprint_not_plaintext(self):
        value = "example-secret-value"
        result = fingerprint(value)
        self.assertNotEqual(result, value)
        self.assertEqual(len(result), 16)

    def test_paper_metadata_valid(self):
        result = validate_vault_metadata(
            mode="paper",
            metadata={
                "schema_version": 1,
                "encryption_provider": "WINDOWS_DPAPI_CURRENT_USER",
                "base_url": "https://paper-api.alpaca.markets",
                "key_fingerprint": "1234567890abcdef",
                "secret_fingerprint": "abcdef1234567890",
                "encrypted_payload_file": "paper_credentials.dpapi",
            },
        )
        self.assertTrue(result["valid"])

    def test_live_endpoint_mismatch_rejected(self):
        result = validate_vault_metadata(
            mode="live",
            metadata={
                "schema_version": 1,
                "encryption_provider": "WINDOWS_DPAPI_CURRENT_USER",
                "base_url": "https://paper-api.alpaca.markets",
                "key_fingerprint": "1234567890abcdef",
                "secret_fingerprint": "abcdef1234567890",
                "encrypted_payload_file": "live_credentials.dpapi",
            },
        )
        self.assertFalse(result["valid"])

    def test_plaintext_fields_rejected(self):
        result = validate_vault_metadata(
            mode="paper",
            metadata={
                "schema_version": 1,
                "encryption_provider": "WINDOWS_DPAPI_CURRENT_USER",
                "base_url": "https://paper-api.alpaca.markets",
                "key_fingerprint": "1234567890abcdef",
                "secret_fingerprint": "abcdef1234567890",
                "encrypted_payload_file": "paper_credentials.dpapi",
                "api_key": "bad",
            },
        )
        self.assertFalse(result["valid"])

    def test_rotation_record_has_no_raw_secret(self):
        result = build_rotation_record(
            mode="paper",
            old_key_fingerprint="old",
            new_key_fingerprint="new",
            reason="rotation",
        )
        self.assertFalse(result["raw_credentials_recorded"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
