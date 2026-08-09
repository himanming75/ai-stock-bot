from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_order_transport_v2_1 import (
    ETradeSandboxOrderTransport,
    ETradeSandboxHTTPError,
)

class TestV211Diagnostic(unittest.TestCase):
    def test_http_400_body_is_preserved(self):
        t=ETradeSandboxOrderTransport("k","s","t","ts",network_enabled=True)
        err=HTTPError(
            "https://apisb.etrade.com/v1/accounts/X/orders/preview.json",
            400,
            "Bad Request",
            {},
            BytesIO(b'{"Error":{"code":102,"message":"Please enter valid account key."}}'),
        )
        with patch("broker_integration_v1.etrade_sandbox_order_transport_v2_1.urlopen",side_effect=err):
            with self.assertRaises(ETradeSandboxHTTPError) as ctx:
                t.post_json("/accounts/X/orders/preview.json",{})
        self.assertEqual(ctx.exception.status,400)
        self.assertIn('"code":102',ctx.exception.response_body)

if __name__=="__main__":
    unittest.main()
