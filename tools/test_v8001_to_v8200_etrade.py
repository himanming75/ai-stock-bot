from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from etrade_sandbox.client import (
    ETradeSandboxReadOnlyClient,
)
from etrade_sandbox.core import (
    normalized_url,
    oauth_header,
    percent_encode,
)
from etrade_sandbox.parsing import (
    extract_accounts,
)
from etrade_sandbox.service import (
    ETradeSandboxCertificationService,
)


class Tests(unittest.TestCase):
    def test_encoding(self):
        self.assertEqual(
            percent_encode("A + B"),
            "A%20%2B%20B",
        )

    def test_url_normalization(self):
        self.assertEqual(
            normalized_url(
                "HTTPS://API.ETRADE.COM:443/oauth/request_token?x=1"
            ),
            "https://api.etrade.com/oauth/request_token",
        )

    def test_oauth_header(self):
        value = oauth_header(
            method="GET",
            url=(
                "https://api.etrade.com/"
                "oauth/request_token"
            ),
            consumer_key="key",
            consumer_secret="secret",
            callback="oob",
            timestamp=1700000000,
            nonce="nonce",
        )
        self.assertIn(
            "oauth_signature=",
            value,
        )

    def test_account_parsing(self):
        items = extract_accounts({
            "data": {
                "AccountListResponse": {
                    "Accounts": {
                        "Account": {
                            "accountIdKey": "abc"
                        }
                    }
                }
            }
        })
        self.assertEqual(
            items[0]["account_id_key"],
            "abc",
        )

    def test_write_block(self):
        client = ETradeSandboxReadOnlyClient(
            consumer_key="key",
            consumer_secret="secret",
            access_token="token",
            access_token_secret="token-secret",
        )
        with self.assertRaises(
            PermissionError
        ):
            client.write_request()

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                ETradeSandboxCertificationService()
                .evaluate(
                    output_dir=Path(d)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                ETradeSandboxCertificationService()
                .evaluate(
                    output_dir=Path(d)
                )
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
