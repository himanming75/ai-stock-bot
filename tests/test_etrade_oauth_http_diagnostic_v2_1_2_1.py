from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_oauth_flow_v2 import (
    ETradeOAuthFlow,
    ETradeOAuthHTTPError,
)


class TestOAuthDiagnosticV2121(unittest.TestCase):
    def test_http_error_body_and_safe_headers_preserved(self):
        err=HTTPError(
            "https://api.etrade.com/oauth/request_token",
            404,
            "Not Found",
            {
                "Content-Type":"text/html",
                "Date":"Sun, 09 Aug 2026 00:00:00 GMT",
                "Authorization":"SHOULD_NOT_LEAK",
            },
            BytesIO(b"diagnostic body"),
        )

        flow=ETradeOAuthFlow(
            "key",
            "secret",
            network_enabled=True,
            callback="oob",
        )

        with patch(
            "broker_integration_v1.etrade_oauth_flow_v2.urlopen",
            side_effect=err,
        ):
            with self.assertRaises(ETradeOAuthHTTPError) as ctx:
                flow.request_token()

        self.assertEqual(ctx.exception.status,404)
        self.assertEqual(
            ctx.exception.response_body,
            "diagnostic body",
        )
        self.assertIn(
            "Content-Type",
            ctx.exception.safe_headers,
        )
        self.assertNotIn(
            "Authorization",
            ctx.exception.safe_headers,
        )


if __name__=="__main__":
    unittest.main()
